"""Auditoria pura de comissões. Não corrige beneficiários nem movimenta dinheiro.

Uma redenção manual/QR não é um recibo Stripe. A ausência de dados corretos
exige conciliação humana: nunca inferir beneficiários pelo nome da campanha.
"""


def payout_evidence(redemption, campaigns, influencers, paid_sessions):
    influencer_id = redemption.get("influencer_id")
    if not influencer_id:
        return "beneficiary_id_missing"
    campaign_id = redemption.get("campaign_id")
    campaign = campaigns.get(campaign_id)
    if not campaign:
        return "campaign_missing"
    if campaign.get("influencer_id") != influencer_id:
        return "campaign_beneficiary_mismatch"
    influencer = influencers.get(influencer_id)
    if not influencer or not influencer.get("nome") or influencer.get("nome") == "—":
        return "beneficiary_not_registered"
    if redemption.get("paid_online") is not True:
        return "manual_redemption_requires_payment_proof"
    session_id = redemption.get("idempotency_key")
    if not session_id or session_id not in paid_sessions:
        return "stripe_payment_not_confirmed"
    return None


REASONS = {
    "beneficiary_id_missing": "ID do influenciador ausente",
    "campaign_missing": "Campanha não localizada",
    "campaign_beneficiary_mismatch": "Beneficiário diferente do associado à campanha",
    "beneficiary_not_registered": "Influenciador não registado ou inativo na base",
    "manual_redemption_requires_payment_proof": "Redenção manual: pagamento financeiro por comprovar",
    "stripe_payment_not_confirmed": "Pagamento Stripe sem confirmação associada",
}


def payout_status(audit_reasons, already_paid=False):
    if already_paid:
        return "Pago"
    if any(reason in audit_reasons for reason in (
        "beneficiary_id_missing", "campaign_missing",
        "campaign_beneficiary_mismatch", "beneficiary_not_registered"
    )):
        return "Atribuição por confirmar"
    if audit_reasons:
        return "Pagamento por confirmar"
    return "Pendente"
