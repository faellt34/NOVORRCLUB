"""Checkout Pix brasileiro exclusivamente em sandbox. Nao efetua repasses.

A rota de Portugal (/public/pay) permanece inalterada. O Pix brasileiro de
producao so sera disponibilizado apos contas Connect e taxas verificadas.
"""
import os
import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from core import db, NO_ID, new_id, now_iso
from stripe_platform import stripe_config, amount_cents, split_snapshot, PaymentConfigurationError
from pix_checkout_logic import require_sandbox_pix, frontend_return_urls, belongs_to_br_test_session, sandbox_payment_intent_data
from payment_safety import is_payment_confirmed

router = APIRouter(prefix="/pix/br/test", tags=["Pix Brasil sandbox"])


class SandboxPixIn(BaseModel):
    code: str
    amount: float
    email: Optional[str] = None


def _sandbox_enabled():
    if os.environ.get("PIX_SANDBOX_ENABLED", "false").strip().lower() != "true":
        raise HTTPException(status_code=503, detail="Checkout Pix de teste desativado")


@router.post("/checkout")
async def create_sandbox_checkout(body: SandboxPixIn):
    """Hosted Checkout, sk_test_ only, no funds transfer or coupon redemption."""
    _sandbox_enabled()
    code = body.code.strip().upper()
    if not code or len(code) > 80:
        raise HTTPException(status_code=400, detail="Cupom invalido")
    campaign = await db.campaigns.find_one({"cupom": code}, NO_ID)
    if not campaign or campaign.get("status") != "Ativa":
        raise HTTPException(status_code=404, detail="Cupom invalido ou inativo")
    partner = await db.partners.find_one({"id": campaign.get("parceiro_id")}, NO_ID)
    if not partner:
        raise HTTPException(status_code=409, detail="Parceiro nao identificado")
    try:
        config = stripe_config(campaign, partner)
        require_sandbox_pix(config)
        gross_cents = amount_cents(body.amount)
        if not 100 <= gross_cents <= 1000000:
            raise PaymentConfigurationError("Valor permitido: R$1 ate R$10.000")
        split = split_snapshot(gross_cents, campaign)
        success_url, cancel_url = frontend_return_urls(os.environ.get("FRONTEND_URL", ""), code)
    except PaymentConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    transaction_id = new_id("pixsandbox")
    record = {
        "id": transaction_id, "kind": "pix_br_test", "country": "BR",
        "campaign_id": campaign["id"], "partner_id": partner["id"],
        "coupon": code, "currency": "brl", "gross_cents": gross_cents,
        "amount_cents": split["paid_cents"], "split_preview": split,
        "session_id": f"creating_{transaction_id}", "payment_status": "pending", "status": "creating",
        "created_at": now_iso(), "updated_at": now_iso(), "transfers_enabled": False,
    }
    await db.payment_transactions.insert_one(dict(record))
    session_args = {
        "mode": "payment", "payment_method_types": ["pix"],
        "line_items": [{"price_data": {
            "currency": "brl", "unit_amount": split["paid_cents"],
            "product_data": {"name": f"{partner.get('nome', 'Parceiro')} - {campaign.get('nome', code)}"},
        }, "quantity": 1}],
        "success_url": success_url, "cancel_url": cancel_url,
        "metadata": {"kind": "pix_br_test", "country": "BR",
                     "transaction_id": transaction_id, "campaign_id": campaign["id"]},
        "payment_intent_data": sandbox_payment_intent_data(transaction_id),
    }
    if body.email:
        session_args["customer_email"] = body.email.strip().lower()
    try:
        session = stripe.checkout.Session.create(
            **session_args, api_key=config["api_key"],
            idempotency_key=f"rrclub_pix_br_test_{transaction_id}",
        )
    except stripe.error.StripeError as exc:
        await db.payment_transactions.update_one(
            {"id": transaction_id, "status": "creating"},
            {"$set": {"status": "checkout_failed", "updated_at": now_iso()}})
        raise HTTPException(status_code=502, detail="Nao foi possivel iniciar o Pix de teste na Stripe") from exc

    await db.payment_transactions.update_one(
        {"id": transaction_id},
        {"$set": {"session_id": session.id, "status": "pending",
                  "updated_at": now_iso()}})
    return {"checkout_url": session.url, "session_id": session.id,
            "currency": "brl", "amount_cents": split["paid_cents"],
            "mode": "test", "transfers_enabled": False}


@router.post("/webhook")
async def sandbox_webhook(request: Request):
    """Independent signed endpoint; never invoke legacy fulfil or transfer APIs."""
    _sandbox_enabled()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET_BR", "")
    if not secret.startswith("whsec_"):
        raise HTTPException(status_code=503, detail="Webhook BR de teste nao configurado")
    try:
        event = stripe.Webhook.construct_event(
            await request.body(), request.headers.get("stripe-signature", ""), secret)
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Assinatura Stripe invalida")
    if event.get("livemode") is not False:
        raise HTTPException(status_code=400, detail="Evento live nao aceito no sandbox")
    event_type = event.get("type")
    if event_type not in (
        "checkout.session.completed", "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed", "checkout.session.expired"
    ):
        return {"received": True, "ignored": True}

    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    if metadata.get("kind") != "pix_br_test":
        return {"received": True, "ignored": True}

    txid = metadata.get("transaction_id")
    record = await db.payment_transactions.find_one({"id": txid}, NO_ID)
    if not record or str(record.get("session_id", "")).startswith("creating_"):
        # Retry after checkout session ID is persisted.
        raise HTTPException(status_code=503, detail="Pagamento ainda sem registro completo")
    if not belongs_to_br_test_session(session, record):
        raise HTTPException(status_code=400, detail="Checkout Pix nao confere com a transacao")

    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if is_payment_confirmed(session):
            await db.payment_transactions.update_one(
                {"id": txid, "session_id": session["id"], "payment_status": {"$ne": "paid"}},
                {"$set": {"payment_status": "paid", "status": "paid_test_only",
                          "paid_at": now_iso(), "updated_at": now_iso()}})
    elif event_type in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        status = "failed" if event_type.endswith("failed") else "expired"
        await db.payment_transactions.update_one(
            {"id": txid, "session_id": session["id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": status, "status": status,
                      "updated_at": now_iso()}})
    return {"received": True, "transfers_executed": False}


@router.get("/status/{session_id}")
async def sandbox_status(session_id: str):
    record = await db.payment_transactions.find_one(
        {"session_id": session_id, "kind": "pix_br_test", "country": "BR"}, NO_ID)
    if not record:
        raise HTTPException(status_code=404, detail="Pagamento de teste nao encontrado")
    return {"session_id": session_id, "payment_status": record["payment_status"],
            "currency": "brl", "amount_cents": record["amount_cents"],
            "transfers_executed": False, "mode": "test"}
