"""Auditoria somente leitura do checkout de cupões Portugal.

Não cria pagamentos, payouts, transfers nem altera o livro financeiro.
O filtro explícito EUR impede misturar transações Pix/BRL.
"""
import asyncio
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, NO_ID, require_role
from finance_evidence import transfer_evidence, connect_account_evidence, charge_cost_evidence

router = APIRouter()

PT_COUPON_QUERY = {
    "kind": "coupon_pay",
    "$or": [{"currency": "eur"}, {"currency": {"$exists": False}}],
}


def _stripe_evidence(session_id, intent_id, expected_amount_minor, destination, expected, commission_minor=None):
    secret = os.environ.get("STRIPE_SECRET_KEY")
    if not secret or not secret.startswith(("sk_live_", "sk_test_", "rk_live_", "rk_test_")):
        raise RuntimeError("Stripe Portugal indisponível")
    session = stripe.checkout.Session.retrieve(session_id, api_key=secret)
    if session.get("payment_status") != "paid":
        return {
            "state": "stripe_session_not_paid",
            "stripe_session_paid": False,
            "bank_payout": "not_verified",
        }
    remote_intent_id = session.get("payment_intent")
    if hasattr(remote_intent_id, "get"):
        remote_intent_id = remote_intent_id.get("id")
    if intent_id and remote_intent_id != intent_id:
        return {"state": "payment_intent_mismatch", "bank_payout": "not_verified"}
    meta = session.get("metadata") or {}
    for key, value in expected.items():
        if meta.get(key) != value:
            return {"state": "session_metadata_mismatch", "bank_payout": "not_verified"}
    if not remote_intent_id:
        return {"state": "missing_payment_intent", "bank_payout": "not_verified"}
    intent = stripe.PaymentIntent.retrieve(remote_intent_id, api_key=secret)
    cid = intent.get("latest_charge")
    if hasattr(cid, "get"):
        cid = cid.get("id")
    charge = stripe.Charge.retrieve(cid, api_key=secret) if cid else None
    balance = None
    if charge and charge.get("balance_transaction"):
        balance_id = charge.get("balance_transaction")
        if hasattr(balance_id, "get"):
            balance_id = balance_id.get("id")
        try:
            balance = stripe.BalanceTransaction.retrieve(balance_id, api_key=secret)
        except stripe.error.StripeError:
            # Falta de detalhe de taxas não pode impedir a prova do pagamento;
            # apresentar taxa como indisponível, nunca como zero.
            balance = None
    fee_evidence = charge_cost_evidence(balance, expected_amount_minor, commission_minor)
    transfer = None
    if charge:
        tid = charge.get("transfer")
        if hasattr(tid, "get"):
            tid = tid.get("id")
        if tid:
            transfer = stripe.Transfer.retrieve(tid, api_key=secret)
    # A associação Partner <-> Connect é verificada pelos IDs, não por nomes.
    # Só expor flags de capacidade, nunca documentos/KYC nem dados pessoais.
    connected = None
    if destination:
        account = stripe.Account.retrieve(destination, api_key=secret)
        connected = connect_account_evidence(account, expected["partner_id"])
    result = transfer_evidence(intent, charge, transfer, expected_amount_minor, destination)
    if connected and connected["account_link_verified"] != "verified":
        result["state"] = "partner_connect_binding_" + connected["account_link_verified"]
        result.pop("transfer_id", None)
        result.pop("transfer_amount_minor", None)
    return {
        **result,
        **fee_evidence,
        "stripe_session_paid": True,
        "payment_method_actual": ((charge or {}).get("payment_method_details") or {}).get("type"),
        "payment_status": intent.get("status"),
        "payment_intent_id": remote_intent_id,
        "stripe_currency": intent.get("currency"),
        "stripe_application_fee_minor": intent.get("application_fee_amount"),
        "transfer_destination": (transfer or {}).get("destination"),
        "partner_connect": connected,
    }


@router.get("/admin/finance/reconciliation")
async def reconciliation_list(
    limit: int = Query(default=40, ge=1, le=100),
    user: dict = Depends(require_role("admin")),
):
    txs = await db.payment_transactions.find(PT_COUPON_QUERY, NO_ID).sort(
        "created_at", -1).limit(limit).to_list(limit)
    partner_ids = list({t["partner_id"] for t in txs if t.get("partner_id")})
    partners = {p["id"]: p.get("nome", "Parceiro") async for p in db.partners.find(
        {"id": {"$in": partner_ids}}, {"_id": 0, "id": 1, "nome": 1})}
    campaign_ids = list({t["campaign_id"] for t in txs if t.get("campaign_id")})
    campaigns = {c["id"]: c async for c in db.campaigns.find(
        {"id": {"$in": campaign_ids}}, {"_id": 0, "id": 1, "influencer_id": 1})}
    influencer_ids = list({
        t.get("influencer_id") or (campaigns.get(t.get("campaign_id")) or {}).get("influencer_id")
        for t in txs
        if t.get("influencer_id") or (campaigns.get(t.get("campaign_id")) or {}).get("influencer_id")
    })
    influencers = {i["id"]: i.get("nome") async for i in db.influencers.find(
        {"id": {"$in": influencer_ids}}, {"_id": 0, "id": 1, "nome": 1})}
    return [
        {
            "session_id": t.get("session_id"),
            "coupon": t.get("coupon"),
            "partner_id": t.get("partner_id"),
            "partner": partners.get(t.get("partner_id"), "Parceiro por identificar"),
            "campaign_id": t.get("campaign_id"),
            "influencer_id": t.get("influencer_id") or (campaigns.get(t.get("campaign_id")) or {}).get("influencer_id"),
            "influencer": influencers.get(
                t.get("influencer_id") or (campaigns.get(t.get("campaign_id")) or {}).get("influencer_id"),
                "Beneficiário por identificar",
            ),
            "attribution_source": "checkout_snapshot" if t.get("influencer_id") else "current_campaign_unverified",
            "influencer_transfer_status": "not_verified",
            "currency": "eur",
            "amount": t.get("amount"),
            "gross_amount": t.get("gross_amount"),
            "payment_status": t.get("payment_status", "not_verified"),
            "distribution_status": t.get("distribution_status", "unverified"),
            "bank_payout_status": "not_verified",
            "created_at": t.get("created_at"),
        }
        for t in txs
    ]


@router.get("/admin/finance/reconciliation/{session_id}")
async def reconciliation_detail(
    session_id: str, user: dict = Depends(require_role("admin"))
):
    tx = await db.payment_transactions.find_one(
        {**PT_COUPON_QUERY, "session_id": session_id}, NO_ID
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transação Portugal não encontrada")
    # Não confiar no ledger local para validar o pagamento real:
    # se o webhook falhou, a verificação admin continua na Stripe (somente leitura).
    if tx.get("amount") is None or not tx.get("campaign_id") or not tx.get("partner_id"):
        return {"state": "missing_transaction_evidence", "bank_payout": "not_verified"}
    partner = await db.partners.find_one({"id": tx["partner_id"]}, NO_ID) or {}
    # A comissão de um pagamento antigo só é apresentada quando o registo
    # financeiro está associado por session_id, cupão, campanha e parceiro.
    redemption = await db.redemptions.find_one({
        "idempotency_key": session_id,
        "$or": [{"currency": "eur"}, {"currency": {"$exists": False}}],
    }, NO_ID)
    commission_minor = None
    if redemption and all(redemption.get(k) == tx.get(k) for k in ("coupon", "campaign_id", "partner_id")):
        raw_commission = redemption.get("commission")
        if isinstance(raw_commission, (int, float)) and raw_commission >= 0:
            commission_minor = int(round(raw_commission * 100))
    expected = {
        "kind": "coupon_pay",
        "campaign_id": tx["campaign_id"],
        "partner_id": tx["partner_id"],
        "coupon": tx.get("coupon"),
    }
    try:
        evidence = await asyncio.to_thread(
            _stripe_evidence,
            session_id,
            tx.get("stripe_payment_intent_id"),
            int(round(float(tx["amount"]) * 100)),
            partner.get("stripe_account_id"),
            expected,
            commission_minor,
        )
        local_state = tx.get("payment_status", "unknown")
        return {
            **evidence,
            "local_payment_status": local_state,
            "ledger_discrepancy": bool(evidence.get("stripe_session_paid") and local_state != "paid"),
        }
    except (stripe.error.StripeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Não foi possível verificar a transação Stripe") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
