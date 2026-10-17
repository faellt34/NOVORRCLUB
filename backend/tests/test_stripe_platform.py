"""Unit tests for production payment guardrails; no money is moved."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stripe_platform import stripe_config, PaymentConfigurationError, split_snapshot, transfer_account

def test_brazil_no_portugal_key_fallback(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY_PT", "sk_test_portugal")
    monkeypatch.delenv("STRIPE_SECRET_KEY_BR", raising=False)
    monkeypatch.setenv("PIX_ENABLED", "true")
    with pytest.raises(PaymentConfigurationError):
        stripe_config({"pais": "Brasil"}, {"pais": "Brasil"})

def test_country_mismatch_rejected(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY_BR", "sk_test_brasil")
    monkeypatch.setenv("PIX_ENABLED", "true")
    with pytest.raises(PaymentConfigurationError):
        stripe_config({"pais": "Portugal"}, {"pais": "Brasil"})

def test_br_pix_feature_flag_required(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY_BR", "sk_test_brasil")
    monkeypatch.delenv("PIX_ENABLED", raising=False)
    with pytest.raises(PaymentConfigurationError):
        stripe_config({"pais": "Brasil"}, {"pais": "Brasil"})

def test_brl_split_snapshot_100_5_10_5_80():
    assert split_snapshot(10000, {"desconto": 5, "comissao_rrclub": 10, "comissao": 5}) == {
        "gross_cents": 10000, "discount_cents": 500, "paid_cents": 9500,
        "rrclub_cents": 1000, "influencer_cents": 500, "partner_cents": 8000}

def test_missing_rrclub_share_blocks_payment():
    with pytest.raises(PaymentConfigurationError):
        split_snapshot(10000, {"desconto": 5, "comissao": 5})

def test_old_pt_connect_account_never_used_in_brazil():
    account = {"stripe_account_id": "acct_pt_example"}
    assert transfer_account(account, "BR") is None
    assert transfer_account(account, "PT") == "acct_pt_example"

def test_invalid_discount_rejected():
    with pytest.raises(PaymentConfigurationError):
        split_snapshot(10000, {"desconto": 150, "comissao": 5, "comissao_rrclub": 10})
