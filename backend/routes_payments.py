import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query, Header
from fastapi.responses import Response
from pydantic import BaseModel

from core import db, NO_ID, get_current_user, require_role, audit, notify, new_id, now_iso, admin_ids
from storage import put_object, get_object, APP_NAME
import jwt

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
TAX_CODE_DIGITAL = "txcd_10302000"
SUBSCRIPTION = {"lookup_key": "club_monthly", "name": "RRclub Premium (mensal)", "amount": 990, "interval": "month", "emergent_product_id": "club_monthly"}

router = APIRouter()


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
    price, eb = await price_for_lookup(body.lookup_key)
    if eb and await db.entitlements.find_one({"user_id": user["id"], "ebook_id": eb["id"]}):
        raise HTTPException(status_code=409, detail="Já adquiriu este e-book")
    kwargs = dict(
        line_items=[{"price": price.id, "quantity": 1}],
        mode="subscription" if price.recurring else "payment",
        success_url=f"{body.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/payment/cancel",
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
            raise HTTPException(status_code=502, detail=f"Stripe: {e.user_message or e}")
    await db.payment_transactions.insert_one({
        "id": new_id("tx"), "session_id": session.id, "user_id": user["id"], "lookup_key": body.lookup_key, "ebook_id": eb["id"] if eb else None,
        "amount": (price.unit_amount or 0) / 100, "currency": price.currency, "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


async def fulfil(session_id: str, extra: dict):
    res = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
        {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso(), **extra}}, projection=NO_ID)
    if not res:
        return
    if res.get("kind") == "coupon_pay":
        c = await db.campaigns.find_one({"id": res["campaign_id"]}, NO_ID)
        partner = await db.partners.find_one({"id": res["partner_id"]}, NO_ID) or {}
        inf = await db.influencers.find_one({"id": c.get("influencer_id")}, NO_ID) if c else None
        rate = float(c["comissao"]) / 100 if c else 0
        gross = float(res["gross_amount"])
        rec = {"id": new_id("r"), "coupon": res["coupon"], "campaign_id": res["campaign_id"], "campaign": c["nome"] if c else "", "partner_id": res["partner_id"], "partner": partner.get("nome", ""),
               "influencer_id": c.get("influencer_id") if c else None, "influencer": inf["nome"] if inf else "—", "amount": round(gross, 2), "discount": round(gross - res["amount"], 2),
               "commission": round(gross * rate, 2), "rate": rate, "date": now_iso(), "staff": "Pagamento online (QR)", "idempotency_key": session_id, "paid_online": True, "payment_method": res.get("payment_method")}
        try:
            await db.redemptions.insert_one(dict(rec))
        except Exception:
            return
        await audit("REDENÇÃO", f"{rec['coupon']} · pago online {res['amount']:.2f}€ (conta {gross:.2f}€) · taxa travada {c['comissao'] if c else 0}% · {rec['partner']}", {"id": "cliente", "nome": "Cliente (QR)"}, rec["id"])
        from realtime import emit
        emit("split_executado", valor_plataforma=rec["commission"], valor_total=rec["amount"], cupom=rec["coupon"], parceiro=rec["partner"], influencer=rec["influencer"], ref=rec["id"], origem="qr",
             influencer_id=rec["influencer_id"], partner_id=rec["partner_id"], record=rec)
        from routes_data import mark_converted
        await mark_converted(rec["campaign_id"], rec)
        targets = await admin_ids()
        pu = await db.users.find_one({"partner_id": res["partner_id"]}, {"id": 1}); iu = await db.users.find_one({"influencer_id": rec["influencer_id"]}, {"id": 1}) if rec["influencer_id"] else None
        targets += [u["id"] for u in (pu, iu) if u]
        await notify(targets, "redencao", "Pagamento online recebido", f"{rec['coupon']} · cliente pagou {res['amount']:.2f}€ em {rec['partner']} · comissão {rec['commission']:.2f}€", "/parceiro")
        cust_email = extra.get("customer_email")
        if cust_email:
            from mailer import send_email
            sent = await send_email(cust_email, f"RRclub · Recibo {rec['coupon']} · {res['amount']:.2f}€", "O seu recibo",
                f"Obrigado! Pagamento confirmado em <b>{rec['partner']}</b>.<br>Conta: {gross:.2f}€ · Desconto ({c['desconto'] if c else 0:g}%): −{rec['discount']:.2f}€ · <b>Pago: {res['amount']:.2f}€</b><br>Cupom {rec['coupon']} · Ref. {rec['id']} · {rec['date'][:16].replace('T', ' ')} UTC",
                "Ver o cupom", f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{rec['coupon']}")
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"customer_email": cust_email, "receipt_emailed": sent, "redemption_id": rec["id"]}})
        else:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"redemption_id": rec["id"]}})
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
    if rec.get("kind") != "coupon_pay":
        user = await user_from_query_or_header(authorization, None)
        if user["role"] != "admin" and rec.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Sem acesso a esta transação")
    if rec["payment_status"] != "paid":
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await fulfil(session_id, {"stripe_subscription_id": s.subscription, "stripe_payment_intent_id": s.payment_intent, "customer_email": (s.customer_details.email if getattr(s, "customer_details", None) else None) or s.customer_email})
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
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid signature")
    obj, t = event["data"]["object"], event["type"]
    if t in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status", "paid") == "paid":
            await fulfil(obj["id"], {"stripe_subscription_id": obj.get("subscription"), "stripe_payment_intent_id": obj.get("payment_intent"), "customer_email": ((obj.get("customer_details") or {}).get("email")) or obj.get("customer_email")})
    elif t in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        st = "failed" if "failed" in t else "expired"
        await db.payment_transactions.update_one({"session_id": obj["id"]}, {"$set": {"status": st, "payment_status": st, "updated_at": now_iso()}})
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
        raise HTTPException(status_code=502, detail=f"Falha no armazenamento: {e}")
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
        raise HTTPException(status_code=502, detail=f"Falha ao obter ficheiro: {e}")
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{eb.get("pdf_name") or ebook_id}.pdf"'})


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
    to_pay = round(body.amount * (1 - float(c["desconto"]) / 100), 2)
    base = dict(
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(round(to_pay * 100)), "product_data": {"name": f"{partner.get('nome', 'Parceiro')} · {c['nome']}", "description": f"Cupom {code} · {c['desconto']:g}% de desconto aplicado sobre {body.amount:.2f}€"}}, "quantity": 1}],
        mode="payment",
        success_url=f"{body.origin_url}/c/{code}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/c/{code}?cancel=1",
        metadata={"kind": "coupon_pay", "coupon": code, "campaign_id": c["id"], "partner_id": c.get("parceiro_id", "")},
    )
    if body.email:
        base["customer_email"] = body.email.strip().lower()
    split = False
    if partner.get("stripe_account_id") and partner.get("stripe_charges_enabled"):
        fee = int(round(body.amount * float(c["comissao"]) / 100 * 100))
        base["payment_intent_data"] = {"application_fee_amount": fee, "transfer_data": {"destination": partner["stripe_account_id"]}, "description": f"{code} · {partner.get('nome')}"}
        split = True
    session = None
    for pm in (["card", "mb_way"], ["card"]):
        try:
            session = stripe.checkout.Session.create(**base, payment_method_types=pm)
            break
        except stripe.error.InvalidRequestError as e:
            if pm == ["card"]:
                raise HTTPException(status_code=502, detail=f"Stripe: {e.user_message or e}")
    await db.payment_transactions.insert_one({"id": new_id("tx"), "session_id": session.id, "user_id": None, "kind": "coupon_pay", "coupon": code, "campaign_id": c["id"], "partner_id": c.get("parceiro_id"),
                                              "gross_amount": round(body.amount, 2), "amount": to_pay, "currency": "eur", "status": "initiated", "payment_status": "pending", "payment_method": "card/mb_way", "split": split, "created_at": now_iso(), "updated_at": now_iso()})
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


@router.post("/partner/connect/onboard")
async def connect_onboard(body: dict, user: dict = Depends(require_role("partner"))):
    partner = await db.partners.find_one({"id": user["partner_id"]}, NO_ID) or {}
    origin = (body.get("origin_url") or "").rstrip("/")
    try:
        acct_id = partner.get("stripe_account_id")
        if not acct_id:
            acct = stripe.Account.create(type="express", country="PT", email=user["email"], business_type="company",
                                         capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
                                         business_profile={"name": partner.get("nome", user["nome"])}, metadata={"partner_id": user["partner_id"]})
            acct_id = acct.id
            await db.partners.update_one({"id": user["partner_id"]}, {"$set": {"stripe_account_id": acct_id, "stripe_charges_enabled": False}})
        link = stripe.AccountLink.create(account=acct_id, refresh_url=f"{origin}/parceiro?connect=refresh", return_url=f"{origin}/parceiro?connect=return", type="account_onboarding")
    except stripe.error.StripeError as e:
        msg = e.user_message or str(e)
        if "signed up for Connect" in msg:
            return {"available": False, "reason": "O Stripe Connect ainda não está ativo na conta Stripe da plataforma. O administrador deve reclamar a conta Stripe e ativar Connect em dashboard.stripe.com/connect. Até lá, os pagamentos entram na conta da plataforma e são transferidos para o seu IBAN manualmente."}
        raise HTTPException(status_code=502, detail=f"Stripe Connect indisponível: {msg}")
    await audit("CONFIGURAÇÃO", f"Onboarding Stripe Connect iniciado · {partner.get('nome')}", user, acct_id)
    return {"available": True, "url": link.url, "account_id": acct_id}


@router.get("/partner/connect/status")
async def connect_status(user: dict = Depends(require_role("partner"))):
    partner = await db.partners.find_one({"id": user["partner_id"]}, NO_ID) or {}
    acct_id = partner.get("stripe_account_id")
    if not acct_id:
        return {"connected": False, "charges_enabled": False, "payouts_enabled": False}
    try:
        a = stripe.Account.retrieve(acct_id)
        info = {"connected": True, "charges_enabled": bool(a.charges_enabled), "payouts_enabled": bool(a.payouts_enabled), "details_submitted": bool(a.details_submitted),
                "bank_last4": (a.external_accounts.data[0].last4 if getattr(a, "external_accounts", None) and a.external_accounts.data else None)}
    except stripe.error.StripeError:
        info = {"connected": True, "charges_enabled": bool(partner.get("stripe_charges_enabled")), "payouts_enabled": False}
    await db.partners.update_one({"id": user["partner_id"]}, {"$set": {"stripe_charges_enabled": info["charges_enabled"], "stripe_payouts_enabled": info["payouts_enabled"]}})
    return info
