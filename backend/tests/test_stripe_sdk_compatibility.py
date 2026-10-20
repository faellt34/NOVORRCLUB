"""Prove Stripe SDK returns non-dict resources and both payment APIs accept them."""
import asyncio
import hashlib
import hmac
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
import stripe

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "rrclub_stripe_sdk_offline")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake_never_network")
os.environ.setdefault("JWT_SECRET", "test-only-local-secret-at-least-32-characters")

from payments.stripe_normalize import StripeRecord, stripe_payload
import routes_pix as pix
import routes_mbway_sandbox as mb
from tests.test_mbway_sandbox import sandbox, request, checkout_body


def signed_resource(data):
    """Real SDK constructs StripeObject from a local signed webhook, no network."""
    body = json.dumps({"id": "evt_offline", "type": "checkout.session.completed",
                       "data": {"object": data}}, separators=(",", ":")).encode()
    ts = int(time.time())
    signature = hmac.new(b"whsec_offline", str(ts).encode()+b"."+body, hashlib.sha256).hexdigest()
    event = stripe.Webhook.construct_event(body, f"t={ts},v1={signature}", "whsec_offline")
    return event["data"]["object"]


def test_real_stripe_object_dict_access_is_normalized():
    payload = signed_resource({
        "id": "cs_test_offline", "livemode": False,
        "metadata": {"kind": "rrclub_mbway_sandbox", "coupon": "P5EUR"},
        "payment_method_types": ["mb_way"], "amount_total": 9500,
    })
    # StripeObject has no dict.get; this failed real HTTP integration until fixed.
    assert not callable(getattr(payload, "get", None))
    normalized = stripe_payload(payload)
    assert isinstance(normalized, StripeRecord)
    assert normalized.id == normalized["id"] == "cs_test_offline"
    assert normalized.get("livemode") is False
    assert normalized["metadata"].get("coupon") == "P5EUR"
    assert normalized["payment_method_types"] == ["mb_way"]


def test_pix_provider_accepts_real_sdk_stripe_objects(monkeypatch):
    client = MagicMock()
    client.v1.accounts.retrieve_current.return_value = signed_resource({
        "country": "BR", "default_currency": "brl", "charges_enabled": True,
        "payouts_enabled": True,
    })
    monkeypatch.setattr(pix, "stripe_client", Mock(return_value=client))
    info = asyncio.run(pix.provider("accounts.retrieve_current"))
    assert info.get("country") == "BR"
    assert info.default_currency == "brl"
    client.v1.accounts.retrieve_current.assert_called_once()


def test_mbway_sandbox_accepts_real_sdk_objects(sandbox):
    sandbox.client.v1.accounts.retrieve_current.return_value = signed_resource({
        "country": "PT", "livemode": False,
    })
    sandbox.client.v1.checkout.sessions.create.return_value = signed_resource({
        "id": "cs_test_mbway", "livemode": False,
        "payment_method_types": ["mb_way"], "url": "https://checkout.stripe.com/c/pay/test",
    })
    result = asyncio.run(mb.checkout(checkout_body(), request()))
    assert result["session_id"] == "cs_test_mbway"
    assert result["mode"] == "test"


def test_mbway_status_accepts_real_sdk_objects(sandbox):
    sandbox.client.v1.checkout.sessions.retrieve.return_value = signed_resource({
        "id": "cs_test_mbway", "livemode": False, "payment_status": "paid",
        "status": "complete",
        "metadata": {"kind": "rrclub_mbway_sandbox", "coupon": "P5EUR"},
    })
    result = asyncio.run(mb.status("cs_test_mbway", "P5EUR"))
    assert result["payment_status"] == "paid_test"
    sandbox.database.redemptions.insert_one.assert_not_awaited()
