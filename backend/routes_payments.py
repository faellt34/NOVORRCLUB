import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional
from urllib.parse import urlsplit

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query, Header
from fastapi.responses import Response
from pydantic import BaseModel

from core import db, NO_ID, get_current_user, require_role, audit, notify, new_id, now_iso, admin_ids
from storage import put_object, get_object, APP_NAME
import jwt

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
TAX_CODE_DIGITAL = "txcd_10302000"
SUBSCRIPTION = {"lookup_key": "club_monthly", "name": "RRclub Premium (mensal)", "amount": 990, "interval": "month", "emergent_product_id": "club_monthly"}

router = APIRouter()
_cfg_cache = {"at": 0, "data": None}


def _stripe_probe() -> dict:
    key = os.environ["STRIPE_SECRET_KEY"]
    info = {"mode": "live" if key.startswith("sk_live") else "test", "account_ok": False, "connect_enabled": False, "webhook_configured": bool(WEBHOOK_SECRET), "account_name": None, "erro": None}
    try:
        acct = stripe.Account.retrieve()
        info.update({"account_ok": True, "account_name": (acct.get("settings") or {}).get("dashboard", {}).get("display_name") or acct.get("business_profile", {}).get("name")})
    except stripe.error.StripeError as e:
        info["erro"] = e.user_message or str(e)[:160]
        return info
    try:
        _v2().v2.core.accounts.list({"limit": 1})
        info["connect_enabled"] = True
    except stripe.StripeError:
        info["connect_enabled"] = False
    # Reading configuration must never create or close connected accounts.
    # A successful list does not certify acceptance of platform responsibilities.
    info["platform_profile_ok"] = None
    return info


async def stripe_config(force: bool = False) -> dict:
    import asyncio, time
    if force or not _cfg_cache["data"] or time.time() - _cfg_cache["at"] > 120:
        _cfg_cache.update({"data": await asyncio.to_thread(_stripe_probe), "at": time.time()})
    return _cfg_cache["data"]


@router.get("/payments/config")
async def payments_config():
    c = await stripe_config()
    return {"mode": c["mode"], "available": c["account_ok"], "connect_enabled": c["connect_enabled"]}


@router.get("/admin/stripe/status")
async def admin_stripe_status(user: dict = Depends(require_role("admin"))):
    c = await stripe_config(force=True)
    partners = await db.partners.count_documents({"status": "Ativo"})
    connected = await db.partners.count_documents({"stripe_charges_enabled": True})
    missing = [p["nome"] async for p in db.partners.find({"status": "Ativo", "stripe_charges_enabled": {"$ne": True}}, {"_id": 0, "nome": 1})]
    steps = [
        {"id": "chave", "label": "Chave Stripe válida" + (f" · {c['account_name']}" if c.get("account_name") else ""), "ok": c["account_ok"], "action": None if c["account_ok"] else f"Verifique STRIPE_SECRET_KEY nos secrets de produção. Erro: {c.get('erro')}"},
        {"id": "modo", "label": f"Modo: {'PAGAMENTOS REAIS (live)' if c['mode'] == 'live' else 'TESTE (sem dinheiro real)'}", "ok": c["mode"] == "live", "action": None if c["mode"] == "live" else "Para receber dinheiro real: reclame a conta Stripe (email da Emergent) → conclua o KYC em dashboard.stripe.com → copie a chave sk_live_… para STRIPE_SECRET_KEY (Re-publish → Secrets) e a pk_live_… para STRIPE_PUBLISHABLE_KEY."},
        {"id": "webhook", "label": "Webhook Stripe configurado (confirma pagamentos automaticamente)", "ok": c["webhook_configured"], "action": None if c["webhook_configured"] else f"Em dashboard.stripe.com → Developers → Webhooks → Add endpoint: {os.environ.get('FRONTEND_URL', '').rstrip('/')}/api/stripe/webhook com o evento checkout.session.completed; copie o whsec_… para STRIPE_WEBHOOK_SECRET."},
        {"id": "connect", "label": "Stripe Connect ativo (split automático 80/5/10)", "ok": c["connect_enabled"], "action": None if c["connect_enabled"] else "Ative Connect em dashboard.stripe.com/connect (tipo Express). Até lá os pagamentos entram na conta RRclub e paga aos hotéis por transferência (IBAN)."},
        {"id": "perfil", "label": "Perfil de plataforma Connect (verificação manual necessária)", "ok": c.get("platform_profile_ok") is True, "action": "Confirme em dashboard.stripe.com → Settings → Connect → Platform profile se os requisitos e responsabilidades estão concluídos. Esta consulta não cria contas para testar a aprovação."},
        {"id": "parceiros", "label": f"Parceiros ligados ao Connect (hotéis, rooftops, restaurantes): {connected}/{partners}", "ok": partners > 0 and connected == partners,
         "action": None if partners > 0 and connected == partners else f"Falta ligar: {', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}. Cada parceiro entra no seu Painel do Parceiro → secção Pagamentos → botão 'Ativar split automático' e conclui o onboarding Stripe (só funciona depois do Connect e do perfil de plataforma estarem ativos)." if missing else "Ainda não há parceiros ativos."},
    ]
    return {"config": c, "steps": steps, "done": sum(1 for s in steps if s["ok"]), "total": len(steps)}


def _product(entry_id: str, name: str):
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if (p.get("metadata") or {}).get("emergent_product_id") == entry_id:
            return p
    return stripe.Product.create(name=name, tax_code=TAX_CODE_DIGITAL, metadata={"managed_by": "emergent", "emergent_product_id": entry_id})


def ensure_price(lookup_key: str, name: str, amount_cents: int, entry_id: str, interval: Optional[str] = None):
    existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
    if existing and existing[0].unit_amount == amount_cents and existing[0].currency == "eur":
        return existing[0]
    if existing:
        stripe.Price.modify(existing[0].id, active=False)
    product = _product(entry_id, name)
    kwargs = dict(product=product.id, unit_amount=amount_cents, currency="eur", lookup_key=lookup_key, transfer_lookup_key=True)
    if interval:
        kwargs["recurring"] = {"interval": interval}
    return stripe.Price.create(**kwargs)


def ensure_tax_settings():
    try:
        s = stripe.tax.Settings.retrieve()
        if s.head_office and getattr(s.head_office, "address", None):
            return
        stripe.tax.Settings.modify(head_office={"address": {"country": "PT", "line1": "Avenida da Liberdade 1", "city": "Lisboa", "postal_code": "1250-096"}}, defaults={"tax_behavior": "exclusive"})
    except Exception:
        pass


async def price_for_lookup(lookup_key: str):
    if lookup_key == SUBSCRIPTION["lookup_key"]:
        return ensure_price(lookup_key, SUBSCRIPTION["name"], SUBSCRIPTION["amount"], SUBSCRIPTION["emergent_product_id"], SUBSCRIPTION["interval"]), None
    if lookup_key.startswith("ebook_"):
        eb = await db.ebooks.find_one({"id": lookup_key[6:]}, NO_ID)
        if not eb or not eb.get("premium") or not eb.get("preco"):
            raise HTTPException(status_code=404, detail="E-book não disponível para compra")
        return ensure_price(lookup_key, eb["titulo"], int(round(float(eb["preco"]) * 100)), lookup_key), eb
    raise HTTPException(status_code=400, detail="Produto desconhecido")


class CheckoutIn(BaseModel):
    lookup_key: str
    origin_url: str


@router.post("/payments/checkout")
async def checkout(body: CheckoutIn, user: dict = Depends(get_current_user)):
    origin = _validated_checkout_origin(body.origin_url)
    price, eb = await price_for_lookup(body.lookup_key)
    if eb and await db.entitlements.find_one({"user_id": user["id"], "ebook_id": eb["id"]}):
        raise HTTPException(status_code=409, detail="Já adquiriu este e-book")
    kwargs = dict(
        line_items=[{"price": price.id, "quantity": 1}],
        mode="subscription" if price.recurring else "payment",
        success_url=f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/payment/cancel",
        customer_email=user["email"],
        metadata={"user_id": user["id"], "lookup_key": body.lookup_key},
    )
    try:
        session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
    except stripe.error.InvalidRequestError as e:
        msg = (e.user_message or str(e)).lower()
        if "managed payments" in msg or "ineligible" in msg:
            session = stripe.checkout.Session.create(**kwargs, automatic_tax={"enabled": True}, billing_address_collection="required")
        else:
            raise HTTPException(status_code=409, detail=f"Stripe: {e.user_message or e}")
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=503, detail=f"Pagamentos temporariamente indisponíveis: {e.user_message or str(e)[:120]}")
    await db.payment_transactions.insert_one({
        "id": new_id("tx"), "session_id": session.id, "user_id": user["id"], "lookup_key": body.lookup_key, "ebook_id": eb["id"] if eb else None,
        "amount": (price.unit_amount or 0) / 100, "currency": price.currency, "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


def _verified_coupon_session(session, transaction):
    """Do not recognize a sale using mismatched Stripe session data."""
    if session is None:
        raise HTTPException(409, "Falta confirmação verificável da sessão Stripe.")
    from payments.stripe_normalize import stripe_payload
    obj = stripe_payload(session)
    metadata = obj.get("metadata") or {}
    try:
        expected_cents = int((Decimal(str(transaction["amount"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, KeyError):
        raise HTTPException(409, "Valor da transação não conciliável.")
    if not (
        obj.get("id") == transaction.get("session_id")
        and obj.get("payment_status") == "paid"
        and obj.get("amount_total") == expected_cents
        and str(obj.get("currency", "")).lower() == str(transaction.get("currency", "")).lower() == "eur"
        and obj.get("livemode") is os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_live_")
        and metadata.get("kind") == "coupon_pay"
        and metadata.get("coupon") == transaction.get("coupon")
        and metadata.get("campaign_id") == transaction.get("campaign_id")
        and metadata.get("partner_id", "") == (transaction.get("partner_id") or "")
    ):
        raise HTTPException(409, "Pagamento não corresponde à transação, valor, moeda ou ambiente Stripe.")
    return obj


async def _fulfil_coupon(transaction: dict, extra: dict):
    """Persist the sale FIRST; only then mark the payment fulfilled.

    A Mongo failure is propagated so Stripe retries the webhook. A stable
    redemption ID makes every retry safe, including crashes between writes.
    """
    import logging
    sid = transaction["session_id"]
    rid = "r-eur-" + sid
    campaign = await db.campaigns.find_one({"id": transaction["campaign_id"]}, NO_ID)
    if not campaign:
        raise HTTPException(503, "Campanha não encontrada; confirmação pendente de conciliação.")
    partner = await db.partners.find_one({"id": transaction["partner_id"]}, NO_ID) or {}
    inf_id = transaction.get("influencer_id", campaign.get("influencer_id"))
    influencer = await db.influencers.find_one({"id": inf_id}, NO_ID) if inf_id else None
    gross = Decimal(str(transaction["gross_amount"]))
    net = Decimal(str(transaction["amount"]))
    pct = Decimal(str(transaction.get("commission_pct", campaign.get("comissao", 0))))
    commission = (gross * pct / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # The provider cannot send a paid event to create records for a different coupon.
    redemption = {
        "id": rid, "coupon": transaction["coupon"],
        "campaign_id": transaction["campaign_id"], "campaign": campaign.get("nome", ""),
        "partner_id": transaction["partner_id"], "partner": partner.get("nome", ""),
        "influencer_id": inf_id, "influencer": (influencer or {}).get("nome", "—"),
        "currency": "eur", "amount": float(gross), "discount": float(gross-net),
        "commission": float(commission), "rate": float(pct)/100,
        "date": now_iso(), "staff": "Pagamento online (QR)",
        "idempotency_key": sid, "paid_online": True,
        "payment_method": transaction.get("payment_method")
    }
    # seed.ensure_indexes() creates a unique "id" index; fixed rid prevents duplicates.
    await db.redemptions.update_one({"id": rid}, {"$setOnInsert": redemption}, upsert=True)
    saved = await db.redemptions.find_one({"id": rid}, NO_ID)
    if not saved or saved.get("coupon") != transaction["coupon"] or saved.get("campaign_id") != transaction["campaign_id"]:
        raise HTTPException(503, "Redenção não conciliada com pagamento Stripe.")
    # This update is the single authoritative commitment that a coupon sale is paid.
    await db.payment_transactions.update_one(
        {"session_id": sid, "kind": "coupon_pay"},
        {"$set": {"status": "completed", "payment_status": "paid",
                  "redemption_id": rid, "stripe_payment_intent_id": extra.get("stripe_payment_intent_id"),
                  "customer_email": extra.get("customer_email"), "updated_at": now_iso()}},
    )
    # Post-payment notifications are non-financial; they must never undo the
    # persisted sale or trigger a second transfer on retries.
    try:
        if not transaction.get("conversion_processed"):
            from routes_data import mark_converted
            await mark_converted(redemption["campaign_id"], saved)
            await db.payment_transactions.update_one(
                {"session_id": sid, "kind": "coupon_pay"},
                {"$set": {"conversion_processed": True}},
            )
        if not transaction.get("notification_processed"):
            await audit("REDENÇÃO",
                f"{redemption['coupon']} · pago online {float(net):.2f}€ · {redemption['partner']}",
                {"id": "cliente", "nome": "Cliente (QR)"}, rid)
            from realtime import emit
            emit("pagamento_atualizado", currency="eur", partner_id=redemption["partner_id"],
                 influencer_id=inf_id, ref=rid)
            targets = await admin_ids()
            pu = await db.users.find_one({"partner_id": redemption["partner_id"]}, {"id": 1})
            iu = await db.users.find_one({"influencer_id": inf_id}, {"id": 1}) if inf_id else None
            targets += [u["id"] for u in (pu, iu) if u]
            await notify(targets, "redencao", "Pagamento online recebido",
                         f"{redemption['coupon']} · pagamento confirmado {float(net):.2f}€", "/parceiro")
            await db.payment_transactions.update_one(
                {"session_id": sid, "kind": "coupon_pay"},
                {"$set": {"notification_processed": True}},
            )
        if extra.get("customer_email") and not transaction.get("receipt_emailed"):
            from mailer import send_email
            sent = await send_email(extra["customer_email"],
                f"RRclub · Recibo {redemption['coupon']} · {float(net):.2f}€",
                "Pagamento confirmado",
                f"Pagamento: {float(net):.2f}€ · Cupom {redemption['coupon']} · Referência {rid}",
                "Consultar cupom",
                f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{redemption['coupon']}")
            await db.payment_transactions.update_one(
                {"session_id": sid, "kind": "coupon_pay"},
                {"$set": {"receipt_emailed": sent}},
            )
    except Exception:
        logging.getLogger(__name__).exception("Post-payment side effects failed for session %s", sid)
        # Retain markers so the reconciliation job can retry safely.


async def fulfil(session_id: str, extra: dict, session_snapshot=None):
    pending = await db.payment_transactions.find_one(
        {"session_id": session_id, "kind": {"$ne": "pix_coupon"}}, NO_ID)
    if not pending:
        return
    if pending.get("kind") == "coupon_pay":
        _verified_coupon_session(session_snapshot, pending)
        if pending.get("payment_status") != "paid" or not pending.get("redemption_id"):
            await _fulfil_coupon(pending, extra)
        return
    if pending.get("payment_status") == "paid":
        return
    res = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "kind": {"$ne": "pix_coupon"}, "payment_status": {"$ne": "paid"}},
        {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso(), **extra}}, projection=NO_ID)
    if not res:
        return
    if res.get("ebook_id"):
        await db.entitlements.update_one({"user_id": res["user_id"], "ebook_id": res["ebook_id"]}, {"$set": {"id": new_id("ent"), "granted_at": now_iso(), "session_id": session_id}}, upsert=True)
        eb = await db.ebooks.find_one({"id": res["ebook_id"]}, NO_ID)
        await audit("COMPRA", f"E-book '{eb['titulo'] if eb else res['ebook_id']}' · {res['amount']:.2f}€", {"id": res["user_id"], "nome": res["user_id"]}, session_id)
        await notify([res["user_id"]], "compra", "Compra confirmada", f"Já pode ler '{eb['titulo']}' na área de E-books.", "/ebooks")
    else:
        await db.subscriptions.update_one({"user_id": res["user_id"]}, {"$set": {"id": new_id("sub"), "status": "active", "stripe_subscription_id": extra.get("stripe_subscription_id"), "started_at": now_iso(), "session_id": session_id}}, upsert=True)
        await audit("SUBSCRIÇÃO", f"RRclub Premium mensal · {res['amount']:.2f}€", {"id": res["user_id"], "nome": res["user_id"]}, session_id)
        await notify([res["user_id"]], "compra", "Subscrição Premium ativa", "Todos os guias premium estão desbloqueados.", "/ebooks")


@router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, authorization: Optional[str] = Header(None)):
    rec = await db.payment_transactions.find_one({"session_id": session_id}, NO_ID)
    if not rec:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    if rec.get("kind") == "pix_coupon":
        raise HTTPException(status_code=409, detail="Este pagamento Pix usa a rota própria de confirmação.")
    if rec.get("kind") != "coupon_pay":
        user = await user_from_query_or_header(authorization, None)
        if user["role"] != "admin" and rec.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Sem acesso a esta transação")
    if rec["payment_status"] != "paid" or (rec.get("kind") == "coupon_pay" and not rec.get("redemption_id")):
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid":
                await fulfil(session_id, {"stripe_subscription_id": getattr(s, "subscription", None), "stripe_payment_intent_id": getattr(s, "payment_intent", None), "customer_email": (getattr(getattr(s, "customer_details", None), "email", None) or getattr(s, "customer_email", None))}, session_snapshot=s)
                rec = await db.payment_transactions.find_one({"session_id": session_id}, NO_ID)
        except stripe.error.StripeError:
            pass
    out = {"session_id": rec["session_id"], "status": rec["status"], "payment_status": rec["payment_status"], "lookup_key": rec.get("lookup_key"), "kind": rec.get("kind"), "amount": rec.get("amount"), "coupon": rec.get("coupon")}
    if rec.get("kind") == "coupon_pay":
        out.update({"gross_amount": rec.get("gross_amount"), "discount": round((rec.get("gross_amount") or 0) - (rec.get("amount") or 0), 2), "redemption_id": rec.get("redemption_id"), "receipt_emailed": rec.get("receipt_emailed"), "customer_email": _mask_email(rec.get("customer_email")), "paid_at": rec.get("updated_at")})
    return out


def _mask_email(e):
    if not e or "@" not in e:
        return None
    n, d = e.split("@", 1)
    return f"{n[:2]}***@{d}"


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook Stripe desativado: STRIPE_WEBHOOK_SECRET não configurado")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), WEBHOOK_SECRET)
        # Stripe SDK events contain StripeObject instances; downstream .get()
        # calls need a plain mapping even when the signature is valid.
        obj = event["data"]["object"]
        if hasattr(obj, "to_dict"):
            event["data"]["object"] = obj.to_dict()
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid signature")
    obj, t = event["data"]["object"], event["type"]
    if (obj.get("metadata") or {}).get("kind") == "pix_coupon":
        # Pix is confirmed only through the separately signed BR webhook.
        return {"status": "ignored", "reason": "dedicated_pix_webhook_required"}
    if t in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") == "paid":
            await fulfil(obj["id"], {"stripe_subscription_id": obj.get("subscription"), "stripe_payment_intent_id": obj.get("payment_intent"), "customer_email": ((obj.get("customer_details") or {}).get("email")) or obj.get("customer_email")}, session_snapshot=obj)
    elif t in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        st = "failed" if "failed" in t else "expired"
        await db.payment_transactions.update_one({"session_id": obj["id"], "kind": {"$ne": "pix_coupon"}, "payment_status": {"$ne": "paid"}}, {"$set": {"status": st, "payment_status": st, "updated_at": now_iso()}})
        if st == "failed":
            from realtime import emit
            emit("erro_transferencia", detalhe=f"Pagamento falhou · sessão {obj['id'][-8:]}", ref=obj["id"])
    elif t in ("transfer.failed", "payout.failed", "transfer.reversed"):
        from realtime import emit
        emit("erro_transferencia", detalhe=f"Stripe {t} · {obj.get('id', '')}", ref=obj.get("id"))
    elif t == "customer.subscription.deleted":
        await db.subscriptions.update_one({"stripe_subscription_id": obj["id"]}, {"$set": {"status": "canceled", "canceled_at": now_iso()}})
    return {"status": "ok"}


async def access_info(user: dict):
    sub = await db.subscriptions.find_one({"user_id": user["id"], "status": "active"}, NO_ID)
    owned = [e["ebook_id"] async for e in db.entitlements.find({"user_id": user["id"]}, NO_ID)]
    return {"subscribed": bool(sub), "owned": owned, "subscription_price": SUBSCRIPTION["amount"] / 100}


@router.get("/payments/access")
async def my_access(user: dict = Depends(get_current_user)):
    return await access_info(user)


@router.post("/admin/ebooks/{ebook_id}/pdf")
async def upload_pdf(ebook_id: str, file: UploadFile = File(...), user: dict = Depends(require_role("admin"))):
    eb = await db.ebooks.find_one({"id": ebook_id}, NO_ID)
    if not eb:
        raise HTTPException(status_code=404, detail="E-book não encontrado")
    if (file.content_type or "") != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas ficheiros PDF")
    data = await file.read()
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF demasiado grande (máx. 40MB)")
    try:
        res = put_object(f"{APP_NAME}/ebooks/{ebook_id}/{uuid.uuid4()}.pdf", data, "application/pdf")
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"Falha no armazenamento: {e}")
    await db.ebooks.update_one({"id": ebook_id}, {"$set": {"pdf_path": res["path"], "pdf_name": file.filename, "pdf_size": res.get("size", len(data)), "pdf_uploaded_at": now_iso()}})
    await audit("UPLOAD", f"PDF de '{eb['titulo']}' · {file.filename}", user, ebook_id)
    return {"ok": True, "pdf_name": file.filename, "pdf_size": res.get("size", len(data))}


async def user_from_query_or_header(authorization: Optional[str], auth: Optional[str]):
    token = auth or (authorization[7:] if authorization and authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = await db.users.find_one({"id": payload["sub"]}, NO_ID)
    if not user:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado")
    return user


@router.get("/ebooks/{ebook_id}/pdf")
async def read_pdf(ebook_id: str, authorization: Optional[str] = Header(None)):
    user = await user_from_query_or_header(authorization, None)
    eb = await db.ebooks.find_one({"id": ebook_id}, NO_ID)
    if not eb or not eb.get("pdf_path"):
        raise HTTPException(status_code=404, detail="Este guia ainda não tem PDF disponível")
    if eb.get("premium") and user["role"] != "admin":
        acc = await access_info(user)
        if not acc["subscribed"] and ebook_id not in acc["owned"]:
            raise HTTPException(status_code=403, detail="Conteúdo premium — compre o guia ou subscreva o RRclub")
    try:
        data, ct = get_object(eb["pdf_path"])
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"Falha ao obter ficheiro: {e}")
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{eb.get("pdf_name") or ebook_id}.pdf"'})


def _validated_checkout_origin(value: str) -> str:
    """Restrict Stripe success/cancel redirects to approved HTTPS origins."""
    origin = str(value or "").strip().rstrip("/")
    allowed_value = os.getenv("PAYMENT_ALLOWED_ORIGINS") or os.getenv("FRONTEND_URL", "")
    allowed = {entry.strip().rstrip("/") for entry in allowed_value.split(",") if entry.strip()}
    try:
        parsed = urlsplit(origin)
        valid = (
            origin in allowed
            and parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or parsed.port > 0)
        )
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(status_code=400, detail="Origem de pagamento não autorizada")
    return origin


class PublicPayIn(BaseModel):
    code: str
    amount: float
    origin_url: str
    email: Optional[str] = None


@router.post("/public/pay")
async def public_pay(body: PublicPayIn):
    code = body.code.strip().upper()
    c = await db.campaigns.find_one({"cupom": code}, NO_ID)
    if not c or c["status"] != "Ativa":
        raise HTTPException(status_code=404, detail="Cupom inválido ou inativo")
    if body.amount < 1 or body.amount > 10000:
        raise HTTPException(status_code=400, detail="Indique o valor da conta (entre 1€ e 10.000€)")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    campaign_currency = str(c.get("currency") or partner.get("currency") or "eur").lower()
    partner_currency = str(partner.get("currency") or "eur").lower()
    if campaign_currency != "eur" or partner_currency != "eur":
        raise HTTPException(status_code=409, detail="Este Checkout aceita apenas campanhas e parceiros em EUR")
    origin = _validated_checkout_origin(body.origin_url)
    to_pay = round(body.amount * (1 - float(c["desconto"]) / 100), 2)
    base = dict(
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(round(to_pay * 100)), "product_data": {"name": f"{partner.get('nome', 'Parceiro')} · {c['nome']}", "description": f"Cupom {code} · {c['desconto']:g}% de desconto aplicado sobre {body.amount:.2f}€"}}, "quantity": 1}],
        mode="payment",
        success_url=f"{origin}/c/{code}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/c/{code}?cancel=1",
        metadata={"kind": "coupon_pay", "coupon": code, "campaign_id": c["id"], "partner_id": c.get("parceiro_id", "")},
    )
    if body.email:
        base["customer_email"] = body.email.strip().lower()
    split = False
    if partner.get("stripe_account_id") and partner.get("stripe_charges_enabled"):
        fee = int(round(body.amount * float(c["comissao"]) / 100 * 100))
        base["payment_intent_data"] = {"application_fee_amount": fee, "transfer_data": {"destination": partner["stripe_account_id"]}, "description": f"{code} · {partner.get('nome')}"}
        split = True
    # Use methods activated for the PT Stripe account. Never silently retry
    # with card-only when MB WAY is rejected: that hides the configuration issue.
    try:
        session = stripe.checkout.Session.create(**base)
    except stripe.error.AuthenticationError:
        raise HTTPException(status_code=503, detail="Pagamentos temporariamente indisponíveis (configuração Stripe). Pague diretamente ao estabelecimento e mostre o cupão.")
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=409, detail=f"Stripe: {e.user_message or str(e)[:120]}")
    await db.payment_transactions.insert_one({"id": new_id("tx"), "session_id": session.id, "user_id": None, "kind": "coupon_pay", "coupon": code, "campaign_id": c["id"], "partner_id": c.get("parceiro_id"),
                                              "gross_amount": round(body.amount, 2), "amount": to_pay, "currency": "eur", "commission_pct": float(c.get("comissao", 0)), "influencer_id": c.get("influencer_id"), "status": "initiated", "payment_status": "pending", "payment_method": "card/mb_way", "split": split, "created_at": now_iso(), "updated_at": now_iso()})
    return {"checkout_url": session.url, "session_id": session.id, "to_pay": to_pay, "discount": round(body.amount - to_pay, 2), "split": split}


class IbanIn(BaseModel):
    iban: str
    titular: Optional[str] = ""


@router.post("/partner/iban")
async def set_iban(body: IbanIn, user: dict = Depends(require_role("partner"))):
    iban = body.iban.replace(" ", "").upper()
    if not (15 <= len(iban) <= 34 and iban[:2].isalpha() and iban[2:4].isdigit()):
        raise HTTPException(status_code=400, detail="IBAN inválido")
    await db.partners.update_one({"id": user["partner_id"]}, {"$set": {"iban": iban, "iban_titular": body.titular.strip()}})
    await audit("CONFIGURAÇÃO", f"IBAN de recebimento atualizado · {user['nome']} · ••••{iban[-4:]}", user, user["partner_id"])
    return {"ok": True, "iban": iban}


CONNECT_INCLUDE = ["configuration.merchant", "configuration.recipient", "requirements"]


def _v2():
    return stripe.StripeClient(os.environ["STRIPE_SECRET_KEY"])


def _connect_create(email: str, nome: str, partner_id: str):
    return _v2().v2.core.accounts.create({
        "contact_email": email, "display_name": nome, "dashboard": "express",
        "identity": {"country": "pt", "entity_type": "company", "business_details": {"registered_name": nome}},
        "defaults": {"responsibilities": {"fees_collector": "application", "losses_collector": "application"}},
        "configuration": {"merchant": {"capabilities": {"card_payments": {"requested": True}}}, "recipient": {"capabilities": {"stripe_balance": {"stripe_transfers": {"requested": True}}}}},
        "metadata": {"partner_id": partner_id}, "include": CONNECT_INCLUDE})


def _connect_link(acct_id: str, origin: str):
    return _v2().v2.core.account_links.create({"account": acct_id, "use_case": {"type": "account_onboarding", "account_onboarding": {
        "configurations": ["merchant", "recipient"], "return_url": f"{origin}/parceiro?connect=return", "refresh_url": f"{origin}/parceiro?connect=refresh"}}})


def _connect_status(acct_id: str) -> dict:
    a = _v2().v2.core.accounts.retrieve(acct_id, {"include": CONNECT_INCLUDE})
    cfg = a.configuration
    card = getattr(getattr(getattr(cfg, "merchant", None), "capabilities", None), "card_payments", None)
    tr = getattr(getattr(getattr(getattr(cfg, "recipient", None), "capabilities", None), "stripe_balance", None), "stripe_transfers", None)
    summary = getattr(getattr(a, "requirements", None), "summary", None)
    pending = bool(summary and getattr(summary, "minimum_deadline", None) and summary.minimum_deadline.status in ("past_due", "currently_due", "eventually_due"))
    return {"connected": True, "charges_enabled": bool(card and card.status == "active"), "payouts_enabled": bool(tr and tr.status == "active"), "details_submitted": not pending}


@router.post("/partner/connect/onboard")
async def connect_onboard(body: dict, user: dict = Depends(require_role("partner"))):
    import asyncio
    import logging
    if not user.get("partner_id"):
        raise HTTPException(status_code=400, detail="A sua conta não está ligada a um estabelecimento. Contacte o administrador.")
    partner = await db.partners.find_one({"id": user["partner_id"]}, NO_ID) or {}
    origin = (body.get("origin_url") or os.environ.get("FRONTEND_URL", "")).rstrip("/")
    try:
        acct_id = partner.get("stripe_account_id")
        if not acct_id:
            acct = await asyncio.to_thread(_connect_create, user["email"], partner.get("nome", user["nome"]), user["partner_id"])
            acct_id = acct.id
            await db.partners.update_one({"id": user["partner_id"]}, {"$set": {"stripe_account_id": acct_id, "stripe_charges_enabled": False}})
        link = await asyncio.to_thread(_connect_link, acct_id, origin)
    except HTTPException:
        raise
    except Exception as e:
        msg = (getattr(e, "user_message", None) or str(e) or type(e).__name__)[:300]
        logging.getLogger(__name__).error(f"connect_onboard falhou ({type(e).__name__}): {msg}")
        if "liability" in msg.lower() or "platform-profile" in msg:
            return {"available": False, "reason": "O Stripe exige que o administrador da RRclub aceite as responsabilidades da plataforma (perdas de contas ligadas) antes de ligar hotéis. Admin: entrar em dashboard.stripe.com → Settings → Connect → Platform profile e concluir o perfil. Até lá, recebe por transferência para o seu IBAN.", "codigo": "liability_unacknowledged"}
        if "Connect" in msg and ("signed up" in msg or "not enabled" in msg.lower() or "platform" in msg.lower()):
            return {"available": False, "reason": "O Stripe Connect ainda não está ativo na conta Stripe da plataforma. O administrador deve ativar Connect em dashboard.stripe.com/connect. Até lá, os pagamentos entram na conta da plataforma e são transferidos para o seu IBAN manualmente."}
        raise HTTPException(status_code=409, detail=f"Stripe Connect indisponível ({type(e).__name__}): {msg}")
    await audit("CONFIGURAÇÃO", f"Onboarding Stripe Connect iniciado · {partner.get('nome')}", user, acct_id)
    return {"available": True, "url": link.url, "account_id": acct_id}


@router.get("/partner/connect/status")
async def connect_status(user: dict = Depends(require_role("partner"))):
    import asyncio
    if not user.get("partner_id"):
        return {"connected": False, "charges_enabled": False, "payouts_enabled": False}
    partner = await db.partners.find_one({"id": user["partner_id"]}, NO_ID) or {}
    acct_id = partner.get("stripe_account_id")
    if not acct_id:
        return {"connected": False, "charges_enabled": False, "payouts_enabled": False}
    try:
        info = await asyncio.to_thread(_connect_status, acct_id)
    except Exception:
        info = {"connected": True, "charges_enabled": bool(partner.get("stripe_charges_enabled")), "payouts_enabled": False}
    await db.partners.update_one({"id": user["partner_id"]}, {"$set": {"stripe_charges_enabled": info["charges_enabled"], "stripe_payouts_enabled": info["payouts_enabled"]}})
    return info
