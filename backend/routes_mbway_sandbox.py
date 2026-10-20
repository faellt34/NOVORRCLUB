"""Clone-only MB WAY Portugal sandbox; never writes financial records or creates payouts."""
import asyncio
import os
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core import NO_ID, db, rate_limit

router = APIRouter()


class MbWayTestIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    amount: float = Field(ge=0.5, le=5000, allow_inf_nan=False)
    origin_url: str


def enabled():
    key = os.getenv("MBWAY_PT_SANDBOX_SECRET_KEY", "")
    return os.getenv("MBWAY_PT_SANDBOX_ENABLED", "").lower() == "true" and key.startswith("sk_test_") and len(key) > 20


def client():
    if not enabled():
        raise HTTPException(503, "MB WAY de teste não configurado. Necessária chave Stripe Portugal sk_test_.")
    return stripe.StripeClient(os.environ["MBWAY_PT_SANDBOX_SECRET_KEY"])


def valid_origin(value):
    origin = value.rstrip("/")
    parsed = urlsplit(origin)
    allowed = {v.strip().rstrip("/") for v in os.getenv("MBWAY_PT_SANDBOX_ALLOWED_ORIGINS", "").split(",") if v.strip()}
    if (origin not in allowed or parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment
        or parsed.username or parsed.password or parsed.hostname in ("rrclub.online", "www.rrclub.online")):
        raise HTTPException(403, "Use apenas o domínio HTTPS de testes do clone.")
    return origin


def net_cents(amount, percent):
    try:
        gross, discount = Decimal(str(amount)), Decimal(str(percent))
        if not gross.is_finite() or not discount.is_finite() or discount < 0 or discount >= 100:
            raise ValueError()
        cents = int((gross * (100 - discount) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
        if not 50 <= cents <= 500000:
            raise ValueError()
        return cents
    except (ValueError, InvalidOperation, TypeError):
        raise HTTPException(400, "O valor MB WAY de teste deve ficar entre 0,50 € e 5.000 €.")


@router.get("/public/mbway-sandbox/availability")
async def availability():
    return {"enabled": enabled(), "method": "mb_way", "currency": "eur", "mode": "test"}


@router.post("/public/mbway-sandbox/checkout")
async def checkout(body: MbWayTestIn, request: Request):
    stripe_client = client()
    origin = valid_origin(body.origin_url)
    code = body.code.strip().upper()
    campaign = await db.campaigns.find_one({"cupom": code}, NO_ID)
    if not campaign or campaign.get("status") != "Ativa" or (campaign.get("currency") or "eur").lower() != "eur":
        raise HTTPException(404, "Este teste exige uma campanha ativa em EUR.")

    await rate_limit("mbway-sandbox:" + (request.client.host if request.client else "unknown"), 12, 3600)
    price = net_cents(body.amount, campaign.get("desconto", 0))
    try:
        account = await asyncio.to_thread(stripe_client.v1.accounts.retrieve_current)
        if account.get("country") != "PT":
            raise HTTPException(409, "É necessária uma conta Stripe de teste de Portugal.")
        session = await asyncio.to_thread(
            stripe_client.v1.checkout.sessions.create,
            params={
                "mode": "payment", "payment_method_types": ["mb_way"],
                "line_items": [{"price_data": {"currency": "eur", "unit_amount": price,
                    "product_data": {"name": "RRClub — teste MB WAY", "description": "Simulação sem dinheiro real."}}, "quantity": 1}],
                "metadata": {"kind": "rrclub_mbway_sandbox", "coupon": code},
                "success_url": origin + "/c/" + code + "?mbway_sandbox_session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": origin + "/c/" + code + "?mbway_sandbox_cancel=1",
            },
            options={"idempotency_key": "rrclub-mbway-test-" + uuid.uuid4().hex},
        )
    except stripe.StripeError as exc:
        raise HTTPException(409, "Stripe Portugal (teste): " + (getattr(exc, "user_message", None) or "MB WAY indisponível nesta conta.")[:180])

    if session.get("livemode") is not False or "mb_way" not in (session.get("payment_method_types") or []) or not session.get("url"):
        raise HTTPException(409, "A Stripe não confirmou uma sessão MB WAY de teste.")
    return {"checkout_url": session["url"], "session_id": session["id"], "mode": "test", "method": "mb_way"}


@router.get("/payments/mbway-sandbox/status/{session_id}")
async def status(session_id: str, coupon: str):
    if not session_id.startswith("cs_test_") or len(session_id) > 255:
        raise HTTPException(400, "Sessão de teste inválida.")
    stripe_client = client()
    try:
        session = await asyncio.to_thread(stripe_client.v1.checkout.sessions.retrieve, session_id)
    except stripe.StripeError:
        raise HTTPException(502, "Não foi possível verificar a simulação na Stripe.")
    meta = session.get("metadata") or {}
    if meta.get("kind") != "rrclub_mbway_sandbox" or meta.get("coupon") != coupon.strip().upper() or session.get("livemode") is not False:
        raise HTTPException(403, "Esta referência não pertence à simulação.")
    state = "paid_test" if session.get("payment_status") == "paid" else ("expired" if session.get("status") == "expired" else "pending")
    # No fulfil(), write to redemptions, commission, conversion or Stripe Connect.
    return {"payment_status": state, "mode": "test", "currency": "eur", "method": "mb_way",
            "message": "Teste concluído — não é um comprovativo de compra." if state == "paid_test" else "Teste pendente ou não concluído."}
