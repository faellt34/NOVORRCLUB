"""Pix checkout sandbox safety: no Stripe, network or database needed."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pix_checkout_logic import require_sandbox_pix, frontend_return_urls, belongs_to_br_test_session
from stripe_platform import PaymentConfigurationError


def test_brazil_sandbox_uses_pix_only_with_isolated_webhook():
    require_sandbox_pix({"country": "BR", "currency": "brl", "api_key": "sk_test_example",
                         "webhook_secret": "whsec_example"})


@pytest.mark.parametrize("config", [
    {"country": "PT", "currency": "eur", "api_key": "sk_test_example", "webhook_secret": "whsec_example"},
    {"country": "BR", "currency": "brl", "api_key": "sk_live_example", "webhook_secret": "whsec_example"},
    {"country": "BR", "currency": "brl", "api_key": "sk_test_example", "webhook_secret": ""},
])
def test_live_wrong_country_or_unverified_webhook_blocked(config):
    with pytest.raises(PaymentConfigurationError):
        require_sandbox_pix(config)


def test_safe_return_urls():
    success, cancel = frontend_return_urls("https://www.rrclub.example/", "BR100")
    assert success == "https://www.rrclub.example/c/BR100?session_id={CHECKOUT_SESSION_ID}"
    assert cancel.endswith("/c/BR100?cancel=1")


@pytest.mark.parametrize("unsafe_url", ["https://evil.com@rrclub.example", "http://rrclub.example",
                                         "https://rrclub.example?next=evil", "javascript:alert(1)"])
def test_unsafe_frontend_urls(unsafe_url):
    with pytest.raises(PaymentConfigurationError):
        frontend_return_urls(unsafe_url, "BR100")


def test_webhook_rejects_wrong_amount_account_or_transaction():
    record = {"id": "tx_abc", "session_id": "cs_test_1", "kind": "pix_br_test",
              "country": "BR", "currency": "brl", "amount_cents": 9500}
    session = {"id": "cs_test_1", "livemode": False, "currency": "brl", "amount_total": 9500,
               "metadata": {"kind": "pix_br_test", "country": "BR", "transaction_id": "tx_abc"}}
    assert belongs_to_br_test_session(session, record)
    assert not belongs_to_br_test_session({**session, "livemode": True}, record)
    assert not belongs_to_br_test_session({**session, "amount_total": 9600}, record)
    assert not belongs_to_br_test_session({**session, "metadata": {**session["metadata"], "transaction_id": "tx_other"}}, record)
