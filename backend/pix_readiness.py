"""Read-only, fail-closed readiness report for RRClub Brasil Pix.

Never expose Stripe secrets; configuration presence is not proof that a live
payment or payout has been validated.
"""
import os
from urllib.parse import urlsplit
from stripe_platform import split_snapshot, PaymentConfigurationError
from payment_region import normalize_country


def pix_environment_snapshot(environ=None):
    env = os.environ if environ is None else environ
    key = env.get("STRIPE_SECRET_KEY_BR", "")
    web = env.get("STRIPE_WEBHOOK_SECRET_BR", "")
    enabled = env.get("PIX_ENABLED", "").strip().lower() == "true"
    sandbox = env.get("PIX_SANDBOX_ENABLED", "").strip().lower() == "true"
    frontend = urlsplit(env.get("FRONTEND_URL", ""))
    valid_frontend = frontend.scheme == "https" and bool(frontend.netloc) and not (
        frontend.username or frontend.password or frontend.query or frontend.fragment
    )
    return {
        "stripe_br_key_mode": "live" if key.startswith("sk_live_") else "test" if key.startswith("sk_test_") else "missing",
        "br_webhook_secret_configured": web.startswith("whsec_"),
        "pix_enabled_flag": enabled,
        "sandbox_enabled_flag": sandbox,
        "frontend_https_configured": valid_frontend,
        "br_production_checkout_implemented": False,
        "br_automatic_transfers_implemented": False,
        "note": "Pix estar ligado na Stripe nao confirma checkout, webhook e repasses do site."
    }


def campaign_readiness(campaign, partner):
    """Return issues for a BR campaign without touching Stripe or MongoDB."""
    issues = []
    c_country = normalize_country(campaign.get("pais") or campaign.get("country"))
    p_country = normalize_country(partner.get("pais") or partner.get("country"))
    if c_country != "BR" or p_country != "BR":
        issues.append("País BR ausente ou divergente entre campanha e parceiro")
    if campaign.get("status") != "Ativa":
        issues.append("Campanha não está ativa")
    if not campaign.get("cupom"):
        issues.append("Cupom não definido")
    for key in ("desconto", "comissao", "comissao_rrclub"):
        if campaign.get(key) in (None, ""):
            issues.append(f"Percentual {key} não definido")
    if not issues:
        try:
            split_snapshot(10000, campaign)
        except (PaymentConfigurationError, ValueError, TypeError) as exc:
            issues.append(str(exc))
    return issues


def payout_link_readiness(person, kind):
    """Stored ID alone never proves account ownership or payout eligibility."""
    account_id = person.get("stripe_account_id_br")
    if not account_id:
        return f"{kind}: conta Connect brasileira nao vinculada"
    if not (isinstance(account_id, str) and account_id.startswith("acct_")):
        return f"{kind}: ID Connect brasileiro invalido"
    return f"{kind}: conta Connect vinculada, mas titularidade/capacidades precisam ser verificadas ao vivo"


def build_pix_br_report(*, campaigns, partners, influencers, environment=None):
    env = pix_environment_snapshot(environment)
    by_partner = {p.get("id"): p for p in partners}
    by_influencer = {i.get("id"): i for i in influencers}
    region_campaigns = [c for c in campaigns if normalize_country(c.get("pais") or c.get("country")) == "BR"]
    entries = []
    for c in region_campaigns:
        partner = by_partner.get(c.get("parceiro_id")) or {}
        issues = campaign_readiness(c, partner)
        inf = by_influencer.get(c.get("influencer_id")) or {}
        if not inf:
            issues.append("Influenciador nao cadastrado")
        if inf and normalize_country(inf.get("pais") or inf.get("country")) != "BR":
            issues.append("Influenciador fora de BR ou sem país cadastrado")
        issues.append(payout_link_readiness(partner, "Parceiro"))
        if inf:
            issues.append(payout_link_readiness(inf, "Influenciador"))
        entries.append({"campaign_id": c.get("id"), "coupon": c.get("cupom"),
                        "blocked": bool(issues), "checks": issues})
    blockers = []
    if env["stripe_br_key_mode"] == "missing":
        blockers.append("Configurar STRIPE_SECRET_KEY_BR na infraestrutura da RRClub, sem enviar a chave pelo chat ou GitHub")
    if not env["br_webhook_secret_configured"]:
        blockers.append("Configurar STRIPE_WEBHOOK_SECRET_BR do ambiente correto")
    if not env["frontend_https_configured"]:
        blockers.append("Configurar FRONTEND_URL HTTPS valido")
    if not env["pix_enabled_flag"]:
        blockers.append("Flag PIX_ENABLED ainda desativada na infraestrutura")
    if not region_campaigns:
        blockers.append("Nenhuma campanha explicitamente brasileira encontrada")
    if not env["br_production_checkout_implemented"]:
        blockers.append("Checkout Pix BR de produção e transferências reais ainda não implementados")
    blockers.append("Validação ponta a ponta do Pix e dos dois repasses ainda não comprovada")
    return {
        "country": "BR", "currency": "brl", "production_ready": False,
        "environment": env,
        "partners_br": sum(normalize_country(p.get("pais") or p.get("country")) == "BR" for p in partners),
        "influencers_br": sum(normalize_country(i.get("pais") or i.get("country")) == "BR" for i in influencers),
        "campaigns_br": len(region_campaigns),
        "campaigns": entries[:100],
        "blockers": blockers,
        "disclaimer": "Auditoria informativa, nao realiza cobrancas, onboarding ou transferencias."
    }
