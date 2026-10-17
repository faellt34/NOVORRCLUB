"""Readiness audit never exposes credentials or declares live processing ready."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pix_readiness import pix_environment_snapshot, build_pix_br_report


def test_no_keys_exposed_and_live_not_claimed():
    env = {"STRIPE_SECRET_KEY_BR": "sk_live_super_private", "STRIPE_WEBHOOK_SECRET_BR": "whsec_private",
           "PIX_ENABLED": "true", "FRONTEND_URL": "https://www.rrclub.example"}
    snapshot = pix_environment_snapshot(env)
    assert snapshot["stripe_br_key_mode"] == "live"
    assert "sk_live_super_private" not in repr(snapshot)
    assert "whsec_private" not in repr(snapshot)
    assert snapshot["br_production_checkout_implemented"] is False


def test_report_flags_legacy_unclassified_partners_and_recipients():
    c = [{"id": "c1", "pais": "BR", "status": "Ativa", "cupom": "RR10",
          "parceiro_id": "p1", "influencer_id": "i1", "desconto": 5, "comissao": 5, "comissao_rrclub": 10}]
    p = [{"id": "p1", "nome": "Parceiro", "pais": "BR"}]
    i = [{"id": "i1", "nome": "Influenciador", "pais": "BR"}]
    result = build_pix_br_report(campaigns=c, partners=p, influencers=i, environment={})
    assert not result["production_ready"]
    assert result["campaigns_br"] == 1
    assert result["campaigns"][0]["blocked"]
    assert any("conta Connect brasileira" in issue for issue in result["campaigns"][0]["checks"])


def test_brazil_currency_never_inferred_from_portugal():
    c = [{"id": "c1", "pais": "BR", "status": "Ativa", "cupom": "R",
          "parceiro_id": "p1", "desconto": 5, "comissao": 5, "comissao_rrclub": 10}]
    p = [{"id": "p1", "pais": "PT"}]
    result = build_pix_br_report(campaigns=c, partners=p, influencers=[], environment={})
    assert any("País BR ausente" in issue for issue in result["campaigns"][0]["checks"])
    assert result["partners_br"] == 0
