"""P5: ligação segura entre QR de uma sessão e cobrança aprovada pelo parceiro.

Nenhuma leitura de QR é registada como pagamento. O P5 é opt-in via P5_ENABLED.
Pix reutiliza o fluxo brasileiro existente quando instalado; nunca troca de conta Stripe.
"""
import asyncio
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, NO_ID, new_id, now_iso, require_role
from finance_evidence import connect_account_evidence

router = APIRouter()


def enabled():
    return os.environ.get("P5_ENABLED", "false").lower() == "true"


def currency_enabled(currency):
    return enabled() and os.environ.get("P5_" + currency.upper() + "_ENABLED", "false").lower() == "true"


def require_enabled(currency=None):
    if not enabled() or (currency and not currency_enabled(currency)):
        raise HTTPException(503, "P5 indisponível para esta moeda. Homologação pendente.")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def minor(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0 or amount > Decimal("10000"):
        raise HTTPException(400, "Valor inválido")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def utc_now():
    return datetime.now(timezone.utc)


def expiration(minutes):
    return (utc_now() + timedelta(minutes=minutes)).isoformat()


class StartSession(BaseModel):
    code: str


class PrepareCharge(BaseModel):
    code: str
    scan_ref: str = Field(min_length=24, max_length=100)
    gross_amount: Decimal = Field(gt=0, le=10000)
    idempotency_key: str = Field(min_length=12, max_length=128)


class CheckoutCharge(BaseModel):
    charge_id: str = Field(min_length=8, max_length=90)
    origin_url: str
    email: str | None = None


@router.get("/public/p5/config")
async def p5_config():
    return {
        "enabled": enabled(),
        "currencies": {"eur": currency_enabled("eur"), "brl": currency_enabled("brl")},
        "requires_partner_approval": True,
        "live_pt_checkout_ready": False,
        "financial_settlement_verified": False,
    }


@router.post("/public/p5/sessions")
async def start_session(body: StartSession):
    require_enabled()
    code = body.code.strip().upper()
    campaign = await db.campaigns.find_one({"cupom": code, "status": "Ativa"}, NO_ID)
    if not campaign:
        raise HTTPException(404, "Cupom inválido ou inativo")
    if campaign.get("validade") and campaign["validade"] < utc_now().date().isoformat():
        raise HTTPException(409, "Cupom expirado")
    partner = await db.partners.find_one({"id": campaign.get("parceiro_id")}, NO_ID) or {}
    currency = str(campaign.get("currency") or partner.get("currency") or "eur").lower()
    require_enabled(currency)
    token = secrets.token_urlsafe(40)
    scan_ref = secrets.token_urlsafe(26)
    await db.p5_sessions.insert_one({
        "id": new_id("p5s"), "code": code, "campaign_id": campaign["id"],
        "scan_ref": scan_ref, "secret_hash": digest(token),
        "created_at": now_iso(), "expires_at": expiration(120),
    })
    # O QR partilha apenas scan_ref; a credencial para consultar/pagar
    # permanece no sessionStorage da aba do seguidor.
    return {"scan_ref": scan_ref, "session_token": token, "expires_at": expiration(120)}


async def owned_session(code, token):
    if not token or len(token) < 30:
        raise HTTPException(401, "Sessão de seguidor necessária")
    session = await db.p5_sessions.find_one(
        {"code": code.strip().upper(), "secret_hash": digest(token)}, NO_ID
    )
    if not session or session["expires_at"] <= now_iso():
        raise HTTPException(403, "Sessão inválida ou expirada")
    return session


@router.post("/partner/p5/charges")
async def partner_charge(body: PrepareCharge, user: dict = Depends(require_role("partner"))):
    require_enabled()
    code = body.code.strip().upper()
    # O parceiro só pode confirmar cobranças de campanhas próprias.
    from partner_access import partner_record
    partner = await partner_record(user, db)
    campaign = await db.campaigns.find_one({"cupom": code, "parceiro_id": partner["id"]}, NO_ID)
    if not campaign or campaign.get("status") != "Ativa":
        raise HTTPException(404, "Campanha não encontrada ou inativa")
    if campaign.get("validade") and campaign["validade"] < utc_now().date().isoformat():
        raise HTTPException(409, "Campanha expirada")
    session = await db.p5_sessions.find_one(
        {"scan_ref": body.scan_ref, "campaign_id": campaign["id"]}, NO_ID
    )
    if not session or session["expires_at"] <= now_iso():
        raise HTTPException(409, "QR P5 inexistente ou sessão expirada. Peça ao seguidor para reabrir o cupom.")
    currency = str(campaign.get("currency") or partner.get("currency") or "eur").lower()
    require_enabled(currency)
    if currency not in ("eur", "brl") or currency != str(partner.get("currency") or currency).lower():
        raise HTTPException(409, "Moeda da campanha e do parceiro incompatíveis")
    gross = minor(body.gross_amount)
    rate = Decimal(str(campaign.get("desconto", 0)))
    if not (Decimal("0") <= rate < Decimal("100")):
        raise HTTPException(409, "Desconto inválido")
    discount = int((Decimal(gross) * rate / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    net = gross - discount
    if net < 50:
        raise HTTPException(409, "Valor após desconto abaixo do mínimo")
    commission_rate = Decimal(str(campaign.get("comissao", 0)))
    if not commission_rate.is_finite() or not 0 <= commission_rate < 100:
        raise HTTPException(409, "Comissão da campanha inválida")
    if currency == "brl" and (rate != 5 or commission_rate != 5):
        raise HTTPException(409, "Pix Brasil P5 exige a campanha 5% desconto / 5% comissão")
    existing = await db.p5_charges.find_one(
        {"partner_id": partner["id"], "idempotency_key": body.idempotency_key}, NO_ID
    )
    if existing:
        if (existing["scan_ref"], existing["coupon"], existing["gross_minor"]) != (body.scan_ref, code, gross):
            raise HTTPException(409, "Referência reutilizada com outra cobrança")
        return {"charge_id": existing["id"], "status": existing["status"], "duplicate": True}
    active = await db.p5_charges.find_one({"scan_ref": body.scan_ref}, NO_ID)
    if active:
        raise HTTPException(409, "Já existe cobrança válida para este QR. Consulte-a antes de criar outra.")
    rec = {
        "id": new_id("p5"), "scan_ref": body.scan_ref,
        "coupon": code, "campaign_id": campaign["id"], "partner_id": partner["id"],
        "gross_minor": gross, "discount_minor": discount, "net_minor": net,
        "influencer_id": campaign.get("influencer_id"),
        "commission_percent_snapshot": str(commission_rate),
        "currency": currency, "status": "pending", "idempotency_key": body.idempotency_key,
        "created_at": now_iso(), "expires_at": expiration(20),
        "session_id": None, "pix_request_id": None, "checkout_url": None,
    }
    try:
        await db.p5_charges.insert_one(rec)
    except DuplicateKeyError:
        existing = await db.p5_charges.find_one({"partner_id": partner["id"], "idempotency_key": body.idempotency_key}, NO_ID)
        if existing and (existing["scan_ref"], existing["coupon"], existing["gross_minor"]) == (body.scan_ref, code, gross):
            return {"charge_id": existing["id"], "status": existing["status"], "duplicate": True}
        raise HTTPException(409, "Este QR já tem uma cobrança associada. Peça um novo QR ao seguidor.")
    return {"charge_id": rec["id"], "status": "pending", "currency": currency,
            "gross_minor": gross, "discount_minor": discount, "net_minor": net}


@router.get("/public/p5/charges/current")
async def current_charge(code: str, x_p5_session: str | None = Header(default=None)):
    require_enabled()
    s = await owned_session(code, x_p5_session)
    rec = await db.p5_charges.find_one({"scan_ref": s["scan_ref"]}, NO_ID, sort=[("created_at", -1)])
    if not rec:
        return {"status": "none"}
    require_enabled(rec["currency"])
    if rec["status"] in ("pending", "creating") and rec["expires_at"] <= now_iso():
        return {"status": "expired"}
    state = rec["status"]
    paid = None
    if rec.get("session_id") or rec.get("pix_request_id"):
        q = {"kind": "coupon_pay", "session_id": rec["session_id"]} if rec.get("session_id") else {"kind": "pix_coupon", "request_id": rec["pix_request_id"]}
        tx = await db.payment_transactions.find_one(q, NO_ID)
        paid = (tx or {}).get("payment_status")
        if paid == "paid":
            state = "paid"
        elif paid in ("failed", "expired"):
            state = paid
    return {"status": state, "charge_id": rec["id"], "currency": rec["currency"],
            "gross_minor": rec["gross_minor"], "discount_minor": rec["discount_minor"],
            "net_minor": rec["net_minor"], "payment_status": paid,
            "checkout_url": rec.get("checkout_url") if state == "checkout" else None,
            "partner_confirmed": True}


@router.post("/public/p5/charges/checkout")
async def checkout_charge(body: CheckoutCharge, x_p5_session: str | None = Header(default=None)):
    require_enabled()
    rec = await db.p5_charges.find_one({"id": body.charge_id}, NO_ID)
    if not rec:
        raise HTTPException(404, "Cobrança não encontrada")
    s = await owned_session(rec["coupon"], x_p5_session)
    if s["scan_ref"] != rec["scan_ref"]:
        raise HTTPException(403, "Esta cobrança pertence a outro seguidor")
    if rec["expires_at"] <= now_iso():
        raise HTTPException(409, "Cobrança expirada. Peça ao parceiro para preparar outra.")
    if rec.get("checkout_url"):
        return {"checkout_url": rec["checkout_url"], "session_id": rec.get("session_id"),
                "pix_request_id": rec.get("pix_request_id")}
    if rec["status"] != "pending":
        raise HTTPException(409, "Esta cobrança já foi iniciada ou concluída")
    campaign = await db.campaigns.find_one({"id": rec["campaign_id"]}, NO_ID)
    partner = await db.partners.find_one({"id": rec["partner_id"]}, NO_ID) or {}
    if not campaign or campaign.get("status") != "Ativa":
        raise HTTPException(409, "Campanha já não está ativa")
    origin = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if not origin.startswith("https://"):
        raise HTTPException(503, "Configure FRONTEND_URL HTTPS para os pagamentos P5")
    if rec["currency"] == "brl":
        # Preserva o ledger, webhook e repasses Pix existentes; ausência do
        # fluxo brasileiro impede qualquer criação de pagamento.
        try:
            from routes_pix import PixCheckoutIn, _checkout
        except ImportError:
            raise HTTPException(503, "Módulo Pix brasileiro ainda não integrado nesta versão")
        request_id = uuid.uuid5(uuid.NAMESPACE_URL, "rrclub:p5:" + rec["id"])
        pix = await _checkout(PixCheckoutIn(code=rec["coupon"],
                                           amount=rec["gross_minor"] / 100,
                                           origin_url=origin, request_id=request_id),
                              creating_partner=rec["partner_id"])
        update = {"status": "checkout", "pix_request_id": str(request_id),
                  "checkout_url": pix["checkout_url"]}
        await db.p5_charges.update_one({"id": rec["id"], "status": "pending"}, {"$set": update})
        return {"checkout_url": pix["checkout_url"], "pix_request_id": str(request_id)}
    if rec["currency"] != "eur":
        raise HTTPException(409, "Moeda não suportada")
    # A origem e o valor vêm do servidor, nunca de um campo editável.
    gross = rec["gross_minor"] / 100
    net = rec["net_minor"] / 100
    data = {
        "mode": "payment",
        "line_items": [{"price_data": {"currency": "eur", "unit_amount": rec["net_minor"],
            "product_data": {"name": f"{partner.get('nome', 'Parceiro')} · {campaign['nome']}",
            "description": f"Campanha {rec['coupon']} · {rec['discount_minor']/100:.2f}€ de desconto"}}, "quantity": 1}],
        "success_url": f"{origin}/c/{rec['coupon']}?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{origin}/c/{rec['coupon']}?cancel=1",
        "metadata": {"kind": "coupon_pay", "p5_charge_id": rec["id"],
                     "campaign_id": rec["campaign_id"], "partner_id": rec["partner_id"], "coupon": rec["coupon"]},
    }
    if body.email and "@" in body.email and len(body.email) <= 254:
        data["customer_email"] = body.email.strip().lower()
    split = False
    if partner.get("stripe_account_id") and partner.get("stripe_charges_enabled"):
        fee = int((Decimal(rec["gross_minor"]) * Decimal(str(campaign.get("comissao", 0))) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if fee > rec["net_minor"]:
            raise HTTPException(409, "Comissão superior ao pagamento")
        data["payment_intent_data"] = {"application_fee_amount": fee,
                                       "transfer_data": {"destination": partner["stripe_account_id"]},
                                       "description": f"P5 {rec['coupon']}"}
        split = True
    try:
        stripe_session = stripe.checkout.Session.create(**data, idempotency_key="p5-" + rec["id"])
    except stripe.error.StripeError as exc:
        raise HTTPException(503, "Stripe indisponível para criar esta cobrança") from exc
    tx = {
        "id": new_id("tx"), "session_id": stripe_session.id,
        "kind": "coupon_pay", "p5_charge_id": rec["id"],
        "coupon": rec["coupon"], "campaign_id": rec["campaign_id"],
        "partner_id": rec["partner_id"], "user_id": None,
        "gross_amount": gross, "amount": net, "currency": "eur",
        "status": "initiated", "payment_status": "pending",
        "payment_method": "stripe_checkout", "split": split,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.payment_transactions.update_one({"session_id": stripe_session.id},
                                              {"$setOnInsert": tx}, upsert=True)
    await db.p5_charges.update_one({"id": rec["id"], "status": "pending"},
                                   {"$set": {"status": "checkout",
                                             "session_id": stripe_session.id,
                                             "checkout_url": stripe_session.url}})
    return {"checkout_url": stripe_session.url, "session_id": stripe_session.id}


async def ensure_p5_indexes():
    await db.p5_sessions.create_index("scan_ref", unique=True)
    await db.p5_sessions.create_index("secret_hash", unique=True)
    await db.p5_charges.create_index("id", unique=True)
    await db.p5_charges.create_index([("partner_id", 1), ("idempotency_key", 1)], unique=True)
    await db.p5_charges.create_index("scan_ref", unique=True)
