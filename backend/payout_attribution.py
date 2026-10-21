"""Validação conservadora de atribuição de comissões.

Não atribuir automaticamente pagamentos a influenciadores por nome ou campanha
se os IDs não corresponderem; pagamentos Pix usam fluxo separado.
"""

REASONS = {
    "beneficiary_id_missing": "ID do influenciador ausente",
    "campaign_missing": "Campanha não localizada",
    "campaign_beneficiary_mismatch": "Influenciador diferente do associado à campanha",
    "beneficiary_not_registered": "Influenciador não identificado na base",
    "manual_redemption_requires_payment_proof": "Redenção manual: cobrança não comprovada",
    "stripe_payment_not_confirmed": "Pagamento Stripe ainda não conciliado",
    "stripe_payment_campaign_mismatch": "Pagamento corresponde a outra campanha, parceiro ou cupão",
    "payment_disputed_or_refunded": "Pagamento suspenso, reembolsado ou contestado",
    "checkout_beneficiary_not_verified": "Checkout antigo sem beneficiário congelado; conciliação manual necessária",
}


def payout_evidence(rec, campaigns, influencers, transactions):
    if rec.get("is_refund") or rec.get("dispute_hold") or rec.get("attribution_hold"):
        return "payment_disputed_or_refunded"
    influencer_id = rec.get("influencer_id")
    if not influencer_id:
        return "beneficiary_id_missing"
    campaign_id = rec.get("campaign_id")
    campaign = campaigns.get(campaign_id)
    if not campaign:
        return "campaign_missing"
    if campaign.get("influencer_id") != influencer_id:
        return "campaign_beneficiary_mismatch"
    inf = influencers.get(influencer_id)
    if not inf or not inf.get("nome") or inf.get("nome") == "—":
        return "beneficiary_not_registered"
    if rec.get("paid_online") is not True:
        return "manual_redemption_requires_payment_proof"
    session_id = rec.get("idempotency_key")
    tx = transactions.get(session_id) if session_id else None
    if not tx or tx.get("kind") != "coupon_pay" or tx.get("payment_status") != "paid":
        return "stripe_payment_not_confirmed"
    if (tx.get("campaign_id") != campaign_id or tx.get("partner_id") != rec.get("partner_id")
            or tx.get("coupon") != rec.get("coupon")):
        return "stripe_payment_campaign_mismatch"
    if tx.get("influencer_id") != influencer_id:
        return "checkout_beneficiary_not_verified"
    return None


def payout_status(reasons, has_manual_record=False):
    if has_manual_record:
        return "Pago"
    if set(reasons) & {
        "beneficiary_id_missing", "campaign_missing",
        "campaign_beneficiary_mismatch", "beneficiary_not_registered",
    }:
        return "Atribuição por confirmar"
    if reasons:
        return "Pagamento por confirmar"
    return "Pendente"
