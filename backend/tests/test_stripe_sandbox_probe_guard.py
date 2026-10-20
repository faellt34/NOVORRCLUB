"""Never contact a live Stripe account from the clone sandbox probe."""
from unittest.mock import Mock
import pytest
from scripts import stripe_sandbox_probe as probe


@pytest.mark.parametrize("secret", [
    "", "sk_live_" + "x" * 40, "rk_live_" + "x" * 40,
    "sk_test_short", "pk_test_" + "x" * 30,
])
def test_provider_probe_rejects_non_test_secret(monkeypatch, secret):
    monkeypatch.setenv("RRCLUB_STRIPE_PT_TEST_KEY", secret)
    client = Mock()
    monkeypatch.setattr(probe.stripe, "StripeClient", client)
    with pytest.raises(RuntimeError):
        probe.safe_key("RRCLUB_STRIPE_PT_TEST_KEY")
    client.assert_not_called()


def test_probe_accepts_sandbox_key_only(monkeypatch):
    monkeypatch.setenv("RRCLUB_STRIPE_PT_TEST_KEY", "sk_test_" + "x" * 30)
    assert probe.safe_key("RRCLUB_STRIPE_PT_TEST_KEY").startswith("sk_test_")
