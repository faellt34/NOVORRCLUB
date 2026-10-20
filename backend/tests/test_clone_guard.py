"""Clone startup must refuse production infrastructure, before ANY DB write."""
import pytest

from clone_guard import require_isolated_clone


@pytest.fixture
def safe(monkeypatch):
    monkeypatch.setenv("RRCLUB_CLONE_ISOLATED", "true")
    monkeypatch.setenv("DB_NAME", "rrclub_clone_unit")
    monkeypatch.setenv("FRONTEND_URL", "https://rrclub-sandbox.preview.example.test")
    monkeypatch.setenv("PAYMENT_ALLOWED_ORIGINS", "https://rrclub-sandbox.preview.example.test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_" + "x"*36)
    monkeypatch.setenv("PIX_STRIPE_SECRET_KEY", "sk_test_" + "b"*36)
    monkeypatch.setenv("MBWAY_PT_SANDBOX_SECRET_KEY", "sk_test_" + "p"*36)
    monkeypatch.delenv("PT_SPLIT_V2_ENABLED", raising=False)
    return monkeypatch


def test_isolated_test_environment_allowed(safe):
    assert require_isolated_clone() is True


@pytest.mark.parametrize("var,value", [
    ("RRCLUB_CLONE_ISOLATED", "false"),
    ("DB_NAME", "test_database"),
    ("DB_NAME", "production"),
    ("DB_NAME", "rrclub_clone_"),
    ("FRONTEND_URL", "https://rrclub.online"),
    ("FRONTEND_URL", "https://www.rrclub.online"),
    ("FRONTEND_URL", "http://rrclub-sandbox.preview.example.test"),
    ("PAYMENT_ALLOWED_ORIGINS", "https://rrclub.online"),
    ("PAYMENT_ALLOWED_ORIGINS", "https://rrclub-sandbox.preview.example.test,https://rrclub.online"),
    ("PAYMENT_ALLOWED_ORIGINS", "http://rrclub-sandbox.preview.example.test"),
    ("STRIPE_SECRET_KEY", "sk_live_"+"x"*36),
    ("PIX_STRIPE_SECRET_KEY", "sk_live_"+"x"*36),
    ("MBWAY_PT_SANDBOX_SECRET_KEY", "sk_live_"+"x"*36),
    ("STRIPE_SECRET_KEY", "sk_test_too_short"),
])
def test_clone_fails_closed_before_db_mutations(safe, var, value):
    safe.setenv(var, value)
    with pytest.raises(RuntimeError, match="Clone locked"):
        require_isolated_clone()


def test_pt_split_requires_test_key_even_with_flag(safe):
    safe.setenv("PT_SPLIT_V2_ENABLED", "true")
    safe.delenv("STRIPE_SECRET_KEY")
    with pytest.raises(RuntimeError, match="Clone locked"):
        require_isolated_clone()


def test_maria_fixtures_can_be_loaded_without_demo_seed(safe):
    assert require_isolated_clone()
    # Maria is a fixture, not an actual Stripe account nor a seeded live user.
