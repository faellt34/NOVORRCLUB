"""Fail-closed monetary reconciliation for RRClub Portugal, clone only.

All requests are in-memory FastAPI; signed Stripe events generated locally.
No real Stripe accounts, banks, emails or production database.
"""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from tests.test_payment_http_integration import pt, request, signed_event, ORIGIN
import routes_payments as pay
from payments.stripe_normalize import stripe_payload


def pt_event(**changes):
    body = {
        "id": "cs_test_pt_http", "payment_status": "paid",
        "amount_total": 9500, "currency": "eur", "livemode": False,
        "payment_intent": "pi_test_reconcile",
        "metadata": {
            "kind": "coupon_pay", "coupon": "EURP5",
            "campaign_id": "cpt", "partner_id": "ppt"
        }
    }
    body.update(changes)
    return {"type": "checkout.session.completed", "data": {"object": body}}


def init_checkout(pt):
    reply = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN,
    })
    assert reply.status_code == 200, reply.text


@pytest.mark.parametrize("changes", [
    {"amount_total": 9400},
    {"amount_total": 9600},
    {"amount_total": None},
    {"currency": "brl"},
    {"currency": None},
    {"livemode": True},
    {"livemode": None},
    {"id": "cs_test_other"},
    {"payment_status": "unpaid"},
    {"metadata": {"kind": "pix_coupon", "coupon": "EURP5", "campaign_id": "cpt", "partner_id": "ppt"}},
    {"metadata": {"kind": "coupon_pay", "coupon": "OTHER", "campaign_id": "cpt", "partner_id": "ppt"}},
    {"metadata": {"kind": "coupon_pay", "coupon": "EURP5", "campaign_id": "other", "partner_id": "ppt"}},
    {"metadata": {"kind": "coupon_pay", "coupon": "EURP5", "campaign_id": "cpt", "partner_id": "other"}},
    {"metadata": {}},
])
def test_pt_payment_cannot_fulfil_mismatched_signed_event(pt, changes):
    init_checkout(pt)
    event = pt_event(**changes)
    raw, headers = signed_event(event, "whsec_local_http_only")
    response = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    # For unpaid or missing IDs, a valid webhook may be acknowledged without writes.
    assert response.status_code in (200, 409), response.text
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0
    tx = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert tx["payment_status"] == "pending", changes


def test_pt_correct_test_payment_fulfils_once(pt):
    init_checkout(pt)
    raw, headers = signed_event(pt_event(), "whsec_local_http_only")
    assert request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers).status_code == 200
    assert request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers).status_code == 200
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1
    tx = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert tx["payment_status"] == "paid"


def test_pt_paid_status_requires_complete_verified_provider_snapshot(pt):
    init_checkout(pt)
    pt.retrieve.return_value = stripe_payload(pt_event(amount_total=9600)["data"]["object"])
    reply = request(pt.app, "GET", "/api/payments/status/cs_test_pt_http")
    assert reply.status_code == 409
    tx = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert tx["payment_status"] == "pending"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0


def test_product_checkout_redirect_is_allowlisted_before_stripe(monkeypatch):
    origin = "https://attacker.example"
    price_lookup = AsyncMock(side_effect=AssertionError("Price must not be loaded"))
    monkeypatch.setattr(pay, "price_for_lookup", price_lookup)
    create = Mock(side_effect=AssertionError("Stripe must not be called"))
    monkeypatch.setattr(pay.stripe.checkout.Session, "create", create)
    monkeypatch.setenv("PAYMENT_ALLOWED_ORIGINS", ORIGIN)
    with pytest.raises(Exception) as exc:
        asyncio.run(pay.checkout(pay.CheckoutIn(lookup_key="club_monthly", origin_url=origin),
                               {"id": "u", "email": "u@example.test"}))
    assert getattr(exc.value, "status_code", None) == 400
    price_lookup.assert_not_awaited()
    create.assert_not_called()


@pytest.mark.parametrize("bad_url", [
    "http://clone.example.test", ORIGIN + "/path", ORIGIN + "?x=1",
    "https://name:password@clone.example.test", "https://rrclub.online",
])
def test_product_checkout_rejects_untrusted_returns(monkeypatch, bad_url):
    monkeypatch.setenv("PAYMENT_ALLOWED_ORIGINS", ORIGIN)
    with pytest.raises(Exception) as exc:
        asyncio.run(pay.checkout(pay.CheckoutIn(lookup_key="club_monthly", origin_url=bad_url),
                               {"id": "u", "email": "u@example.test"}))
    assert getattr(exc.value, "status_code", None) == 400
