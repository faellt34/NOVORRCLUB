"""Pix provider: actionable Connect errors, safe logging, no new live accounts."""
import asyncio
import pytest
from fastapi import HTTPException
from tests.test_pix_service import env
import routes_pix as pix

def test_connect_configuration_denied_returns_409_instead_of_502(env, caplog):
    client = pix.stripe.StripeClient() if False else pix.stripe.StripeClient
    mocked = client.return_value
    failure = pix.stripe.error.StripeError("mock remote failed")
    failure.http_status = 403
    failure.code = "platform_profile_missing"
    failure.request_id = "req_test_safe"
    mocked.v1.account_links.create.side_effect = failure
    with pytest.raises(HTTPException) as err:
        asyncio.run(pix.connect_onboard(
            {"origin_url":"https://rrclub.online"},
            {"role":"partner","partner_id":"p","email":"no-private-data@invalid.test","nome":"Test"}))
    assert err.value.status_code == 409
    assert "Stripe Connect Brasil" in err.value.detail
    assert "req_test_safe" in caplog.text
    assert "sk_test_pix_br" not in caplog.text

def test_stripe_timeout_remains_retryable_502(env, caplog):
    mocked = pix.stripe.StripeClient.return_value
    mocked.v1.payment_intents.retrieve.side_effect = pix.stripe.error.APIConnectionError("simulated-timeout")
    with pytest.raises(HTTPException) as err:
        asyncio.run(pix.provider("payment_intents.retrieve","pi_test_mock"))
    assert err.value.status_code == 502
    assert "payment_intents.retrieve" in caplog.text
    assert "sk_test_pix_br" not in caplog.text
