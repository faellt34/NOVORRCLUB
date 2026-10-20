"""Isolated HTTP integration tests: real FastAPI routes, signatures, mocked Stripe and Mongo.

No live accounts, network, webhook destinations, transfers, or real payments.
"""
import asyncio
import hashlib
import hmac
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI
from mongomock_motor import AsyncMongoMockClient

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "rrclub_http_only")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake_offline_no_stripe_calls")
os.environ.setdefault("JWT_SECRET", "test-only-local-secret-at-least-32-characters")

import routes_mbway_sandbox as mb
import routes_payments as pay
import routes_pix as pix

from tests.test_mbway_sandbox import sandbox
from tests.test_pix_service import env, KEY, paid

ORIGIN = "https://clone.example.test"


def http_app(router):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def request(app, method, path, **kwargs):
    async def call():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN,
            timeout=4.0,
        ) as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(call())


def signed_event(event, secret):
    """Generate a real Stripe-Signature header; Stripe's SDK verifies it."""
    body = json.dumps(event, separators=(",", ":")).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return body, {"stripe-signature": f"t={timestamp},v1={digest}", "content-type": "application/json"}


@pytest.fixture
def pt(monkeypatch):
    db = AsyncMongoMockClient().rrclub_pt_http_only
    monkeypatch.setattr(pay, "db", db)
    monkeypatch.setenv("PAYMENT_ALLOWED_ORIGINS", ORIGIN)
    monkeypatch.setenv("FRONTEND_URL", ORIGIN)
    monkeypatch.setattr(pay, "WEBHOOK_SECRET", "whsec_local_http_only")
    session = SimpleNamespace(
        id="cs_test_pt_http", url="https://checkout.stripe.com/c/pay/isolated_test",
        livemode=False,
    )
    created = Mock(return_value=session)
    retrieve = Mock(return_value=SimpleNamespace(
        payment_status="unpaid", status="complete",
    ))
    monkeypatch.setattr(pay.stripe.checkout.Session, "create", created)
    monkeypatch.setattr(pay.stripe.checkout.Session, "retrieve", retrieve)
    monkeypatch.setattr(pay, "audit", AsyncMock())
    monkeypatch.setattr(pay, "notify", AsyncMock())
    monkeypatch.setattr(pay, "admin_ids", AsyncMock(return_value=[]))
    import routes_data
    monkeypatch.setattr(routes_data, "mark_converted", AsyncMock())
    import realtime
    monkeypatch.setattr(realtime, "emit", Mock())
    asyncio.run(db.campaigns.insert_one({
        "id": "cpt", "cupom": "EURP5", "nome": "Campanha Teste",
        "status": "Ativa", "currency": "eur", "desconto": 5,
        "comissao": 5, "parceiro_id": "ppt", "influencer_id": None,
    }))
    asyncio.run(db.partners.insert_one({
        "id": "ppt", "nome": "Parceiro Sandbox", "currency": "eur",
    }))
    return SimpleNamespace(app=http_app(pay.router), db=db, created=created, retrieve=retrieve)


def test_portugal_checkout_to_signed_webhook_to_one_redemption(pt):
    payload = {"code": "EURP5", "amount": 100, "origin_url": ORIGIN}
    init = request(pt.app, "POST", "/api/public/pay", json=payload)
    assert init.status_code == 200, init.text
    assert init.json()["session_id"] == "cs_test_pt_http"
    assert init.json()["to_pay"] == 95
    params = pt.created.call_args.kwargs
    assert params["line_items"][0]["price_data"]["unit_amount"] == 9500
    assert params["line_items"][0]["price_data"]["currency"] == "eur"
    assert params["success_url"].startswith(ORIGIN)
    assert "payment_method_types" not in params
    assert asyncio.run(pt.db.payment_transactions.count_documents({"kind": "coupon_pay"})) == 1
    # A completed but unpaid Stripe Checkout Session cannot deliver.
    pending = request(pt.app, "GET", "/api/payments/status/cs_test_pt_http")
    assert pending.status_code == 200
    assert pending.json()["payment_status"] == "pending"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0
    # Use real signature verification, but no Stripe network or payment.
    event = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_test_pt_http", "payment_status": "paid",
        "currency": "eur", "amount_total": 9500, "livemode": False,
        "payment_intent": "pi_test_http", "metadata": {"kind": "coupon_pay", "coupon": "EURP5", "campaign_id": "cpt", "partner_id": "ppt"},
    }}}
    body, headers = signed_event(event, "whsec_local_http_only")
    paid_reply = request(pt.app, "POST", "/api/stripe/webhook", content=body, headers=headers)
    assert paid_reply.status_code == 200, paid_reply.text
    assert paid_reply.json()["status"] == "ok"
    # Retry webhook to prove idempotency through the real HTTP route.
    retry = request(pt.app, "POST", "/api/stripe/webhook", content=body, headers=headers)
    assert retry.status_code == 200
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1
    rec = asyncio.run(pt.db.redemptions.find_one({"coupon": "EURP5"}))
    assert rec["amount"] == 100 and rec["discount"] == 5 and rec["commission"] == 5
    final = request(pt.app, "GET", "/api/payments/status/cs_test_pt_http")
    assert final.status_code == 200 and final.json()["payment_status"] == "paid"
    assert final.json()["redemption_id"] == rec["id"]


def test_portugal_invalid_signed_webhook_does_not_confirm(pt):
    assert request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN,
    }).status_code == 200
    event = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_test_pt_http", "payment_status": "paid",
    }}}
    body, headers = signed_event(event, "whsec_invalid_not_the_test_secret")
    response = request(pt.app, "POST", "/api/stripe/webhook", content=body, headers=headers)
    assert response.status_code == 400
    rec = asyncio.run(pt.db.payment_transactions.find_one({"session_id": "cs_test_pt_http"}))
    assert rec["payment_status"] == "pending"
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0


@pytest.mark.parametrize("event_type", ["checkout.session.completed", "checkout.session.async_payment_succeeded"])
@pytest.mark.parametrize("payment_status", ["unpaid", "no_payment_required"])
def test_portugal_unpaid_event_cannot_deliver(pt, event_type, payment_status):
    assert request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN,
    }).status_code == 200
    event = {"type": event_type, "data": {"object": {
        "id": "cs_test_pt_http", "payment_status": payment_status,
    }}}
    body, headers = signed_event(event, "whsec_local_http_only")
    assert request(pt.app, "POST", "/api/stripe/webhook", content=body, headers=headers).status_code == 200
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0


@pytest.mark.parametrize("origin", [
    "https://rrclub.online", "https://other.example.test",
    "http://clone.example.test", ORIGIN + "/evil",
])
def test_portugal_redirect_must_stay_inside_clone(pt, origin):
    result = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": origin,
    })
    assert result.status_code == 400, result.text
    pt.created.assert_not_called()
    assert asyncio.run(pt.db.payment_transactions.count_documents({})) == 0


@pytest.mark.parametrize("amount", [0, -5, 10001])
def test_portugal_invalid_amount_cannot_create_checkout(pt, amount):
    result = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": amount, "origin_url": ORIGIN,
    })
    assert result.status_code == 400
    pt.created.assert_not_called()


def test_brazil_campaign_never_uses_portuguese_checkout(pt):
    asyncio.run(pt.db.campaigns.update_one({"cupom": "EURP5"}, {"$set": {"currency": "brl"}}))
    result = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN,
    })
    assert result.status_code == 409
    pt.created.assert_not_called()


def test_mbway_sandbox_http_availability_checkout_status(sandbox):
    app = http_app(mb.router)
    available = request(app, "GET", "/api/public/mbway-sandbox/availability")
    assert available.status_code == 200
    assert available.json() == {"enabled": True, "method": "mb_way", "currency": "eur", "mode": "test"}
    checkout = request(app, "POST", "/api/public/mbway-sandbox/checkout", json={
        "code": "P5EUR", "amount": 100, "origin_url": "https://clone-rrclub.preview.example.test",
    })
    assert checkout.status_code == 200, checkout.text
    options = sandbox.client.v1.checkout.sessions.create.call_args.kwargs["params"]
    assert options["line_items"][0]["price_data"]["unit_amount"] == 9500
    assert options["payment_method_types"] == ["mb_way"]
    status = request(app, "GET", "/api/payments/mbway-sandbox/status/cs_test_mock?coupon=P5EUR")
    assert status.status_code == 200, status.text
    assert status.json()["payment_status"] == "paid_test"
    sandbox.database.redemptions.insert_one.assert_not_awaited()
    sandbox.database.payment_transactions.insert_one.assert_not_awaited()


def test_mbway_sandbox_http_refuses_live_key(sandbox, monkeypatch):
    monkeypatch.setenv("MBWAY_PT_SANDBOX_SECRET_KEY", "sk_live_" + "x"*28)
    result = request(http_app(mb.router), "POST", "/api/public/mbway-sandbox/checkout", json={
        "code": "P5EUR", "amount": 100, "origin_url": "https://clone-rrclub.preview.example.test",
    })
    assert result.status_code == 503
    sandbox.client.v1.checkout.sessions.create.assert_not_called()


def test_pix_http_checkout_signed_webhook_split_once(env, monkeypatch):
    app = http_app(pix.router)
    for route in app.routes:
        if route.path == "/api/partner/pix/checkout":
            for dependency in route.dependant.dependencies:
                app.dependency_overrides[dependency.call] = lambda: {"partner_id": "p"}
    payload = {
        "code": "TEST", "amount": 100,
        "origin_url": "https://rrclub.online",
        "request_id": KEY,
    }
    checkout = request(app, "POST", "/api/partner/pix/checkout", json=payload)
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["amount"] == 95
    assert checkout.json()["platform_amount"] == 10
    assert len(env[0].payment_transactions.items) == 1
    # An unpaid session must not create a redemption or any recipient transfer.
    unpaid = paid()
    unpaid["payment_status"] = "unpaid"
    event = {"type": "checkout.session.completed", "data": {"object": unpaid}}
    body, headers = signed_event(event, "whsec_test")
    assert request(app, "POST", "/api/stripe/pix/webhook", content=body, headers=headers).status_code == 200
    assert not env[0].redemptions.items
    assert env[1].call_count == 1
    assert pix.stripe_client().v1.transfers.create.call_count == 0
    # Confirm paid event and retry it to validate deduplication.
    event["data"]["object"] = paid()
    body, headers = signed_event(event, "whsec_test")
    response = request(app, "POST", "/api/stripe/pix/webhook", content=body, headers=headers)
    assert response.status_code == 200, response.text
    retry = request(app, "POST", "/api/stripe/pix/webhook", content=body, headers=headers)
    assert retry.status_code == 200, retry.text
    assert len(env[0].redemptions.items) == 1
    transfers = pix.stripe_client().v1.transfers.create.call_args_list
    assert [call.kwargs["params"]["amount"] for call in transfers] == [8000, 500]
    assert len(env[0].payment_transactions.items) == 1
    assert env[0].payment_transactions.items[0]["split_status"] == "completed"
    outcome = request(app, "GET", "/api/payments/pix/status/" + KEY)
    assert outcome.status_code == 200
    assert outcome.json()["payment_status"] == "paid"
    assert outcome.json()["split_status"] == "completed"
