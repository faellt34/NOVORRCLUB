"""Admin financial contract, no external services or real Stripe calls."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from campaign_guardrails import validate_admin_payment_fields, legacy_eur_checkout_allowed

def test_new_partner_requires_explicit_country():
    with pytest.raises(ValueError):
        validate_admin_payment_fields("parceiros", {"nome": "Novo"}, True)

def test_no_default_country_on_old_record():
    assert validate_admin_payment_fields("parceiros", {"pais": ""}, False, {"nome": "Legado"}) == {}

def test_brazil_campaign_needs_rrclub_share():
    with pytest.raises(ValueError):
        validate_admin_payment_fields("campanhas", {"pais": "BR", "desconto": "5", "comissao": "5"}, True)

def test_valid_negotatiated_split_is_retained():
    result=validate_admin_payment_fields("campanhas", {"pais": "Brasil", "desconto": "5", "comissao": "5", "comissao_rrclub": "10"}, True)
    assert result == {"pais":"BR","desconto":5,"comissao":5,"comissao_rrclub":10}

@pytest.mark.parametrize("rrclub",["nan","inf","-1","110"])
def test_invalid_rrclub_commission_rejected(rrclub):
    with pytest.raises(ValueError):
        validate_admin_payment_fields("campanhas", {"pais":"BR","desconto":"5","comissao":"5","comissao_rrclub":rrclub}, True)

def test_existing_brazil_requires_verified_commission():
    with pytest.raises(ValueError):
        validate_admin_payment_fields("campanhas", {"nome":"Editado"}, False, {"pais":"BR","comissao":5,"desconto":5})

def test_legacy_eur_checkout_denies_brazil_or_unknown():
    assert legacy_eur_checkout_allowed({"pais":"PT"},{"pais":"PT"})
    assert legacy_eur_checkout_allowed({}, {})
    assert not legacy_eur_checkout_allowed({"pais":"BR"},{"pais":"BR"})
    assert not legacy_eur_checkout_allowed({"pais":"PT"},{"pais":"BR"})
    assert not legacy_eur_checkout_allowed({"pais":"zz"},{"pais":"PT"})
