"""Offline MB WAY sandbox regressions; Stripe and MongoDB always mocked."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "rrclub_clone_offline")
os.environ.setdefault("JWT_SECRET", "offline-test-key-with-more-than-32-characters")

import routes_mbway_sandbox as mb

run = asyncio.run
ORIGIN = "https://clone-rrclub.preview.example.test"


@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setenv("MBWAY_PT_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("MBWAY_PT_SANDBOX_SECRET_KEY", "sk_test_" + "x" * 28)
    monkeypatch.setenv("MBWAY_PT_SANDBOX_ALLOWED_ORIGINS", ORIGIN)
    client = Mock()
    client.v1.accounts.retrieve_current.return_value = {"country": "PT"}
    client.v1.checkout.sessions.create.return_value = {
        "id": "cs_test_mock", "url": "https://checkout.stripe.com/c/pay/cs_test_mock",
        "livemode": False, "payment_method_types": ["mb_way"],
    }
    client.v1.checkout.sessions.retrieve.return_value = {
        "id": "cs_test_mock", "livemode": False, "payment_status": "paid",
        "status": "complete", "metadata": {"kind": "rrclub_mbway_sandbox", "coupon": "P5EUR"},
    }
    monkeypatch.setattr(mb.stripe, "StripeClient", Mock(return_value=client))
    campaign = SimpleNamespace(find_one=AsyncMock(return_value={
        "cupom": "P5EUR", "status": "Ativa", "currency": "eur", "desconto": 5,
    }))
    transactions = SimpleNamespace(insert_one=AsyncMock(), update_one=AsyncMock())
    redemptions = SimpleNamespace(insert_one=AsyncMock())
    database = SimpleNamespace(campaigns=campaign, payment_transactions=transactions, redemptions=redemptions)
    monkeypatch.setattr(mb, "db", database)
    limiter = AsyncMock()
    monkeypatch.setattr(mb, "rate_limit", limiter)
    return SimpleNamespace(client=client, database=database, limiter=limiter)


def request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def checkout_body(origin=ORIGIN, amount=100):
    return mb.MbWayTestIn(code="P5EUR", amount=amount, origin_url=origin)


def assert_no_money_written(sandbox):
    sandbox.database.payment_transactions.insert_one.assert_not_awaited()
    sandbox.database.payment_transactions.update_one.assert_not_awaited()
    sandbox.database.redemptions.insert_one.assert_not_awaited()


def test_sandbox_reports_disabled_without_test_key(sandbox, monkeypatch):
    monkeypatch.delenv("MBWAY_PT_SANDBOX_SECRET_KEY")
    assert run(mb.availability()) == {"enabled": False, "method": "mb_way", "currency": "eur", "mode": "test"}
    with pytest.raises(HTTPException) as error:
        run(mb.checkout(checkout_body(), request()))
    assert error.value.status_code == 503
    sandbox.client.v1.checkout.sessions.create.assert_not_called()


@pytest.mark.parametrize("key", ["sk_live_" + "x" * 30, "rk_test_" + "x" * 30, "sk_test_short"])
def test_rejects_live_or_invalid_secret(sandbox, monkeypatch, key):
    monkeypatch.setenv("MBWAY_PT_SANDBOX_SECRET_KEY", key)
    assert run(mb.availability())["enabled"] is False
    with pytest.raises(HTTPException) as error:
        mb.client()
    assert error.value.status_code == 503
    sandbox.client.v1.checkout.sessions.create.assert_not_called()


@pytest.mark.parametrize("origin", [
    "https://rrclub.online", "https://www.rrclub.online",
    "http://clone-rrclub.preview.example.test",
    "https://other.example.test",
    ORIGIN + "/payment", ORIGIN + "?payment=1", ORIGIN + "#fragment",
    "https://someone:password@clone-rrclub.preview.example.test",
])
def test_rejects_untrusted_checkout_origins(sandbox, origin):
    with pytest.raises(HTTPException) as error:
        run(mb.checkout(checkout_body(origin=origin), request()))
    assert error.value.status_code == 403
    sandbox.client.v1.accounts.retrieve_current.assert_not_called()
    sandbox.client.v1.checkout.sessions.create.assert_not_called()
    assert_no_money_written(sandbox)


def test_checkout_uses_test_mbway_eur_p5_and_is_read_only(sandbox):
    reply = run(mb.checkout(checkout_body(amount=100), request()))
    assert reply["mode"] == "test"
    assert reply["method"] == "mb_way"
    assert reply["session_id"] == "cs_test_mock"
    kwargs = sandbox.client.v1.checkout.sessions.create.call_args.kwargs
    params = kwargs["params"]
    assert params["payment_method_types"] == ["mb_way"]
    assert params["line_items"][0]["price_data"]["currency"] == "eur"
    assert params["line_items"][0]["price_data"]["unit_amount"] == 9500
    assert params["metadata"] == {"kind": "rrclub_mbway_sandbox", "coupon": "P5EUR"}
    assert params["success_url"].startswith(ORIGIN + "/c/P5EUR?")
    assert kwargs["options"]["idempotency_key"].startswith("rrclub-mbway-test-")
    assert_no_money_written(sandbox)


@pytest.mark.parametrize("invalid_campaign", [
    None, {"status": "Suspenso", "currency": "eur"},
    {"status": "Ativa", "currency": "brl"},
])
def test_non_eur_or_inactive_campaign_never_calls_stripe(sandbox, invalid_campaign):
    sandbox.database.campaigns.find_one.return_value = invalid_campaign
    with pytest.raises(HTTPException) as error:
        run(mb.checkout(checkout_body(), request()))
    assert error.value.status_code == 404
    sandbox.client.v1.accounts.retrieve_current.assert_not_called()
    sandbox.client.v1.checkout.sessions.create.assert_not_called()


def test_rejects_non_portugal_stripe_account(sandbox):
    sandbox.client.v1.accounts.retrieve_current.return_value = {"country": "BR"}
    with pytest.raises(HTTPException) as error:
        run(mb.checkout(checkout_body(), request()))
    assert error.value.status_code == 409
    sandbox.client.v1.checkout.sessions.create.assert_not_called()
    assert_no_money_written(sandbox)


@pytest.mark.parametrize("response_change", [
    {"livemode": True}, {"payment_method_types": ["card"]}, {"url": None},
])
def test_rejects_live_or_non_mbway_checkout_session(sandbox, response_change):
    original = sandbox.client.v1.checkout.sessions.create.return_value
    sandbox.client.v1.checkout.sessions.create.return_value = {**original, **response_change}
    with pytest.raises(HTTPException) as error:
        run(mb.checkout(checkout_body(), request()))
    assert error.value.status_code == 409
    assert_no_money_written(sandbox)


def test_paid_sandbox_status_is_never_financial_fulfilment(sandbox):
    result = run(mb.status("cs_test_mock", "P5EUR"))
    assert result["payment_status"] == "paid_test"
    assert result["mode"] == "test"
    assert "não é um comprovativo" in result["message"]
    assert_no_money_written(sandbox)


@pytest.mark.parametrize("change", [
    {"livemode": True}, {"metadata": {"kind": "coupon_pay", "coupon": "P5EUR"}},
    {"metadata": {"kind": "rrclub_mbway_sandbox", "coupon": "OUTRO"}},
])
def test_sandbox_status_rejects_wrong_session_identity(sandbox, change):
    original = sandbox.client.v1.checkout.sessions.retrieve.return_value
    sandbox.client.v1.checkout.sessions.retrieve.return_value = {**original, **change}
    with pytest.raises(HTTPException) as error:
        run(mb.status("cs_test_mock", "P5EUR"))
    assert error.value.status_code == 403
    assert_no_money_written(sandbox)


@pytest.mark.parametrize("session", ["cs_live_wrong", "invalid", "cs_test_" + "x" * 260])
def test_status_rejects_non_test_reference_before_stripe(sandbox, session):
    with pytest.raises(HTTPException) as error:
        run(mb.status(session, "P5EUR"))
    assert error.value.status_code == 400
    sandbox.client.v1.checkout.sessions.retrieve.assert_not_called()


@pytest.mark.parametrize("payment_status,state,expected", [
    ("unpaid", "open", "pending"), ("unpaid", "expired", "expired"),
    ("paid", "complete", "paid_test"),
])
def test_status_mapping_is_only_a_demo(sandbox, payment_status, state, expected):
    sandbox.client.v1.checkout.sessions.retrieve.return_value.update({
        "payment_status": payment_status, "status": state,
    })
    result = run(mb.status("cs_test_mock", "P5EUR"))
    assert result["payment_status"] == expected
    assert_no_money_written(sandbox)


@pytest.mark.parametrize("gross,discount,expected", [
    (100, 5, 9500), (20, 5, 1900), (0.50, 0, 50),
    (12.34, 5, 1172),
])
def test_p5_uses_decimal_minor_units(gross, discount, expected):
    assert mb.net_cents(gross, discount) == expected
