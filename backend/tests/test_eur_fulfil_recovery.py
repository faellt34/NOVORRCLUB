"""EUR coupon payment recovery when the database or worker fails.

Locally signed webhook and mongomock only: zero Stripe/network calls.
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from tests.test_payment_http_integration import pt, request, signed_event, ORIGIN
import routes_payments as pay


def start(pt):
    answer = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN
    })
    assert answer.status_code == 200, answer.text


def paid_event():
    return signed_event({"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_test_pt_http", "payment_status": "paid", "currency": "eur",
        "amount_total": 9500, "livemode": False, "payment_intent": "pi_test_recover",
        "metadata": {
            "kind": "coupon_pay", "coupon": "EURP5",
            "campaign_id": "cpt", "partner_id": "ppt"
        }
    }}}, "whsec_local_http_only")


def test_failed_sale_write_keeps_payment_retriable(pt, monkeypatch):
    start(pt)
    original = pay._fulfil_coupon
    calls = 0

    async def fail_before_persist(tx, extra):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("DB temporarily unavailable in mock")
        return await original(tx, extra)

    monkeypatch.setattr(pay, "_fulfil_coupon", fail_before_persist)
    raw, headers = paid_event()
    first = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    assert first.status_code == 500
    before = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert before["payment_status"] == "pending"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0
    second = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    assert second.status_code == 200
    after = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert after["payment_status"] == "paid"
    assert after["redemption_id"] == "r-eur-cs_test_pt_http"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1
    assert request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers).status_code == 200
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1


def test_legacy_paid_without_redemption_can_recover_using_paid_status(pt):
    start(pt)
    asyncio.run(pt.db.payment_transactions.update_one(
        {"session_id": "cs_test_pt_http"},
        {"$set": {"payment_status": "paid", "status": "completed"},
         "$unset": {"redemption_id": ""}}
    ))
    from payments.stripe_normalize import StripeRecord
    pt.retrieve.return_value = StripeRecord({
        "id": "cs_test_pt_http", "payment_status": "paid", "amount_total": 9500,
        "currency": "eur", "livemode": False, "payment_intent": "pi_test_restore",
        "metadata": {
            "kind": "coupon_pay", "coupon": "EURP5",
            "campaign_id": "cpt", "partner_id": "ppt"
        }
    })
    response = request(pt.app, "GET", "/api/payments/status/cs_test_pt_http")
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == "paid"
    assert response.json()["redemption_id"] == "r-eur-cs_test_pt_http"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1


def test_coupon_sale_idempotent_after_partial_write(pt):
    start(pt)
    # Crash occurred AFTER first insert but BEFORE marking payment paid.
    asyncio.run(pt.db.redemptions.insert_one({
        "id": "r-eur-cs_test_pt_http", "idempotency_key": "cs_test_pt_http",
        "coupon": "EURP5", "campaign_id": "cpt", "amount": 100,
    }))
    raw, headers = paid_event()
    response = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    assert response.status_code == 200, response.text
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1
    assert asyncio.run(pt.db.payment_transactions.find_one(
        {"session_id": "cs_test_pt_http"}, {"_id": 0, "redemption_id": 1}
    )) == {"redemption_id": "r-eur-cs_test_pt_http"}
