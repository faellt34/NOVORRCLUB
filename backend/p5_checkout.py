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
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, NO_ID, new_id, now_iso, require_role, rate_limit, client_ip
from p5_rules import quote_minor, P5QuoteError

router = APIRouter()


def enabled():
    return os.environ.get("P5_ENABLED", "false").lower() == "true"


def currency_enabled(currency):
    if not enabled() or os.environ.get("P5_" + currency.upper() + "_ENABLED", "false").lower() != "true":
        return False
    if currency == "eur":
        # Do not offer checkout with live funds before a verified PT beneficiary policy.
        return os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_")
    if currency == "brl":
        from routes_pix import availability_configuration
        return availability_configuration()[0]["accepting_new_payments"]
    return False


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
async def start_session(body: StartSession, request: Request):
    require_enabled()
    # Only a bounded number of anonymous QR sessions can be opened per IP.
    hashed_ip = hashlib.sha256(client_ip(request).encode()).hexdigest()[:24]
    await rate_limit("p5-start-" + hashed_ip, 30, 3600)
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
    try:
        quote = quote_minor(
            body.gross_amount, campaign.get("desconto", 0),
            campaign.get("comissao", 0), currency,
        )
    except P5QuoteError as exc:
        raise HTTPException(409, str(exc)) from exc
    gross, discount, net = quote["gross_minor"], quote["discount_minor"], quote["net_minor"]
    commission_rate = quote["commission_percent_snapshot"]
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
        "commission_percent_snapshot": commission_rate,
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


def _pt_stripe_checkout(rec, campaign, partner, origin, customer_email):
    """Portugal: test-mode P5 only until verified recipient split is implemented.

    Never treat a destination charge / platform receipt as proof of influencer transfer.
    Do not use a live key for this P5 route before the distribution policy is approved.
    """
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        raise HTTPException(
            503,
            "P5 Portugal em homologação. A divisão financeira e os destinatários devem ser certificados antes de cobrar em produção.",
        )
    metadata = {
        "kind": "coupon_pay",
        "p5_charge_id": rec["id"],
        "campaign_id": rec["campaign_id"],
        "partner_id": rec["partner_id"],
        "influencer_id": rec.get("influencer_id") or "",
        "coupon": rec["coupon"],
        "commission_percent_snapshot": str(rec["commission_percent_snapshot"]),
    }
    base = dict(
        api_key=key,
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": rec["net_minor"],
                "product_data": {
                    "name": f"{partner.get('nome', 'Parceiro')} · {campaign['nome']}",
                    "description": f"P5 {rec['coupon']} · desconto confirmado no estabelecimento",
                },
            },
            "quantity": 1,
        }],
        success_url=f"{origin}/c/{rec['coupon']}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/c/{rec['coupon']}?cancel=1",
        metadata=metadata,
        payment_intent_data={"metadata": metadata, "description": f"P5 {rec['coupon']}"},
    )
    if customer_email:
        base["customer_email"] = customer_email
    try:
        return stripe.checkout.Session.create(
            **base,
            payment_method_types=["card", "mb_way"],
            idempotency_key="p5-" + rec["id"] + "-mbway",
        )
    except stripe.error.InvalidRequestError:
        return stripe.checkout.Session.create(
            **base,
            payment_method_types=["card"],
            idempotency_key="p5-" + rec["id"] + "-card",
        )


@router.post("/public/p5/charges/checkout")
async def checkout_charge(body: CheckoutCharge, x_p5_session: str | None = Header(default=None)):
    require_enabled()
    rec = await db.p5_charges.find_one({"id": body.charge_id}, NO_ID)
    if not rec:
        raise HTTPException(404, "Cobrança não encontrada")
    require_enabled(rec["currency"])
    follower_session = await owned_session(rec["coupon"], x_p5_session)
    if follower_session["scan_ref"] != rec["scan_ref"]:
        raise HTTPException(403, "Cobrança pertence a outra sessão de seguidor")
    if rec["expires_at"] <= now_iso():
        raise HTTPException(409, "Cobrança expirada. Peça ao parceiro para preparar outra.")
    if rec.get("checkout_url"):
        return {
            "checkout_url": rec["checkout_url"],
            "session_id": rec.get("session_id"),
            "pix_request_id": rec.get("pix_request_id"),
        }
    if rec["status"] != "pending":
        raise HTTPException(409, "Cobrança em preparação. Aguarde e consulte a mesma referência.")

    from routes_pix import trusted_origin, availability_configuration
    origin = trusted_origin(body.origin_url)
    campaign = await db.campaigns.find_one({"id": rec["campaign_id"]}, NO_ID)
    partner = await db.partners.find_one({"id": rec["partner_id"]}, NO_ID)
    if not campaign or campaign.get("status") != "Ativa" or not partner:
        raise HTTPException(409, "Campanha ou estabelecimento indisponível")
    if campaign.get("validade") and campaign["validade"] < utc_now().date().isoformat():
        raise HTTPException(409, "Campanha expirada")
    if campaign.get("parceiro_id") != rec["partner_id"]:
        raise HTTPException(409, "Associação de parceiro alterada; confirme com o administrador")
    # A campanha pode ter sido editada depois da leitura do QR.
    # Nunca cobrar se os valores, a moeda ou o beneficiário foram modificados.
    if (
        str(campaign.get("influencer_id") or "") != str(rec.get("influencer_id") or "")
        or str(Decimal(str(campaign.get("comissao", 0)))) != str(Decimal(str(rec["commission_percent_snapshot"])))
        or (campaign.get("currency") or partner.get("currency") or "eur") != rec["currency"]
    ):
        raise HTTPException(409, "Campanha modificada após aprovação. Gere um novo QR.")
    discount_rate = Decimal(str(campaign.get("desconto", 0)))
    expected_discount = int((Decimal(rec["gross_minor"]) * discount_rate / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if expected_discount != rec["discount_minor"] or rec["gross_minor"] - expected_discount != rec["net_minor"]:
        raise HTTPException(409, "Desconto alterado. Não é possível cobrar esta conta.")
    if rec["currency"] == "brl" and not availability_configuration()[0]["accepting_new_payments"]:
        raise HTTPException(503, "Pix Brasil ainda não habilitado no servidor")
    # Portugal P5 live is withheld until a verified two-beneficiary split is designed.
    if rec["currency"] == "eur" and not os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
        raise HTTPException(503, "P5 Portugal ainda não homologado para pagamentos reais")

    # Atomic claim protects against follower double-click; Stripe/Pix idempotency
    # protects retry after a partial network/database failure.
    claimed = await db.p5_charges.find_one_and_update(
        {"id": rec["id"], "status": "pending"},
        {"$set": {"status": "creating", "checkout_started_at": now_iso()}},
        projection=NO_ID,
    )
    if not claimed:
        latest = await db.p5_charges.find_one({"id": rec["id"]}, NO_ID)
        if latest and latest.get("checkout_url"):
            return {
                "checkout_url": latest["checkout_url"],
                "session_id": latest.get("session_id"),
                "pix_request_id": latest.get("pix_request_id"),
            }
        raise HTTPException(409, "Cobrança em preparação. Não inicie uma segunda.")

    try:
        if rec["currency"] == "brl":
            # Existing Pix module alone owns Brazil Stripe key, ledger,
            # signed webhook, cashback reversal and both idempotent transfers.
            from routes_pix import PixCheckoutIn, _checkout
            request_id = uuid.uuid5(uuid.NAMESPACE_URL, "rrclub:p5:" + rec["id"])
            pix = await _checkout(
                PixCheckoutIn(
                    code=rec["coupon"],
                    amount=rec["gross_minor"] / 100,
                    origin_url=origin,
                    request_id=request_id,
                ),
                creating_partner=rec["partner_id"],
            )
            update = {
                "status": "checkout", "pix_request_id": str(request_id),
                "checkout_url": pix["checkout_url"],
            }
            result = {"checkout_url": pix["checkout_url"], "pix_request_id": str(request_id)}
        elif rec["currency"] == "eur":
            email = body.email.strip().lower() if body.email and "@" in body.email and len(body.email) <= 254 else None
            stripe_session = await asyncio.to_thread(
                _pt_stripe_checkout, rec, campaign, partner, origin, email
            )
            tx = {
                "id": new_id("tx"),
                "session_id": stripe_session.id,
                "kind": "coupon_pay",
                "p5_charge_id": rec["id"],
                "coupon": rec["coupon"],
                "campaign_id": rec["campaign_id"],
                "partner_id": rec["partner_id"],
                "influencer_id": rec.get("influencer_id"),
                "commission_percent_snapshot": float(rec["commission_percent_snapshot"]),
                "user_id": None,
                "gross_amount": rec["gross_minor"] / 100,
                "amount": rec["net_minor"] / 100,
                "currency": "eur",
                "status": "initiated",
                "payment_status": "pending",
                "payment_method": "stripe_checkout_mbway_card",
                "split": False,
                "distribution_status": "manual_reconciliation_required",
                "commission_settlement_status": "accrued_unpaid",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            await db.payment_transactions.update_one(
                {"session_id": stripe_session.id}, {"$setOnInsert": tx}, upsert=True
            )
            update = {
                "status": "checkout", "session_id": stripe_session.id,
                "checkout_url": stripe_session.url,
            }
            result = {"checkout_url": stripe_session.url, "session_id": stripe_session.id}
        else:
            raise HTTPException(409, "Moeda P5 inválida")

        await db.p5_charges.update_one(
            {"id": rec["id"], "status": "creating"},
            {"$set": {**update, "checkout_updated_at": now_iso()}},
        )
        return result
    except (stripe.error.StripeError, HTTPException):
        await db.p5_charges.update_one(
            {"id": rec["id"], "status": "creating"},
            {"$set": {"status": "pending", "checkout_error_at": now_iso()}},
        )
        raise
    except Exception as exc:
        await db.p5_charges.update_one(
            {"id": rec["id"], "status": "creating"},
            {"$set": {"status": "pending", "checkout_error_at": now_iso()}},
        )
        raise HTTPException(503, "Cobrança em verificação. Reabra a mesma sessão antes de tentar novamente.") from exc


async def ensure_p5_indexes():
    await db.p5_sessions.create_index("scan_ref", unique=True)
    await db.p5_sessions.create_index("secret_hash", unique=True)
    await db.p5_charges.create_index("id", unique=True)
    await db.p5_charges.create_index([("partner_id", 1), ("idempotency_key", 1)], unique=True)
    await db.p5_charges.create_index("scan_ref", unique=True)
