"""Consulta financeira de leitura apenas: não gera transferências nem payouts.

Um PaymentIntent sucedido não prova que um parceiro ou influencer recebeu dinheiro.
Apenas um Transfer real da Stripe demonstra transferência para uma conta Connect;
o payout bancário exige verificação independente.
"""
import asyncio
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, NO_ID, require_role

router = APIRouter()


def transfer_evidence(intent, charge=None, transfer=None, expected_amount=None, expected_destination=None):
    """Classifica provas da Stripe sem transformar checkout em comprovativo bancário."""
    if intent.get("status") != "succeeded":
        return {"state": "payment_not_succeeded", "bank_payout": "not_verified"}
    if expected_amount is not None and intent.get("amount") != expected_amount:
        return {"state": "amount_mismatch", "bank_payout": "not_verified"}
    if not charge or not charge.get("transfer"):
        return {"state": "no_transfer_evidence", "bank_payout": "not_verified"}
    if not transfer or transfer.get("id") != charge.get("transfer"):
        return {"state": "transfer_not_verifiable", "bank_payout": "not_verified"}
    if expected_destination and transfer.get("destination") != expected_destination:
        return {"state": "destination_mismatch", "bank_payout": "not_verified"}
    if transfer.get("reversed") or transfer.get("amount_reversed", 0):
        return {"state": "reversed_or_partially_reversed", "bank_payout": "not_verified"}
    return {"state": "transferred_to_connected_stripe_account", "bank_payout": "not_verified",
            "transfer_id": transfer.get("id"), "transfer_amount_minor": transfer.get("amount"),
            "transfer_currency": transfer.get("currency")}


def _stripe_evidence(intent_id, expected_amount, expected_destination):
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise RuntimeError("Stripe não configurado neste ambiente")
    intent = stripe.PaymentIntent.retrieve(intent_id)
    charge = None
    transfer = None
    charge_id = intent.get("latest_charge")
    if isinstance(charge_id, dict):
        charge_id = charge_id.get("id")
    if charge_id:
        charge = stripe.Charge.retrieve(charge_id)
        transfer_id = charge.get("transfer")
        if isinstance(transfer_id, dict):
            transfer_id = transfer_id.get("id")
        if transfer_id:
            transfer = stripe.Transfer.retrieve(transfer_id)
    result = transfer_evidence(intent, charge, transfer, expected_amount, expected_destination)
    return {**result, "stripe_payment_status": intent.get("status"),
            "payment_intent_id": intent.get("id"), "stripe_currency": intent.get("currency"),
            "stripe_transfer_destination": (transfer or {}).get("destination"),
            "stripe_application_fee_minor": intent.get("application_fee_amount")}


@router.get("/admin/finance/reconciliation")
async def reconciliation_list(limit: int = Query(default=40, ge=1, le=100),
                              user: dict = Depends(require_role("admin"))):
    txs = await db.payment_transactions.find(
        {"kind": "coupon_pay"}, NO_ID
    ).sort("created_at", -1).limit(limit).to_list(limit)
    ids = list({tx.get("partner_id") for tx in txs if tx.get("partner_id")})
    partners = {p["id"]: p.get("nome", "Parceiro") async for p in db.partners.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "nome": 1})}
    return [{"session_id": tx.get("session_id"), "payment_intent_id": tx.get("stripe_payment_intent_id"),
             "coupon": tx.get("coupon"), "partner": partners.get(tx.get("partner_id"), "—"),
             "partner_id": tx.get("partner_id"), "amount": tx.get("amount"),
             "gross_amount": tx.get("gross_amount"), "currency": tx.get("currency"),
             "payment_status": tx.get("payment_status"),
             "distribution_status": tx.get("distribution_status", "legacy_unverified"),
             "bank_payout_status": "not_verified",
             "created_at": tx.get("created_at")} for tx in txs]


@router.get("/admin/finance/reconciliation/{session_id}")
async def reconciliation_detail(session_id: str, user: dict = Depends(require_role("admin"))):
    tx = await db.payment_transactions.find_one(
        {"kind": "coupon_pay", "session_id": session_id}, NO_ID)
    if not tx:
        raise HTTPException(404, "Pagamento de cupão não encontrado")
    if tx.get("payment_status") != "paid":
        return {"state": "payment_not_confirmed", "bank_payout": "not_verified"}
    intent_id = tx.get("stripe_payment_intent_id")
    if not intent_id:
        # Transações antigas podem não ter o ID gravado; procurar sem modificar dados.
        try:
            session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
            intent_id = session.get("payment_intent")
        except stripe.error.StripeError as exc:
            raise HTTPException(502, "Não foi possível confirmar a sessão na Stripe") from exc
    if not intent_id:
        return {"state": "missing_payment_intent", "bank_payout": "not_verified"}
    partner = await db.partners.find_one({"id": tx.get("partner_id")}, NO_ID) or {}
    amount = tx.get("amount")
    if amount is None:
        return {"state": "missing_amount", "bank_payout": "not_verified"}
    try:
        evidence = await asyncio.to_thread(
            _stripe_evidence, intent_id, int(round(float(amount) * 100)),
            partner.get("stripe_account_id")
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(502, "Stripe indisponível para reconciliação") from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if evidence.get("stripe_currency") != tx.get("currency"):
        evidence["state"] = "currency_mismatch"
    return evidence
