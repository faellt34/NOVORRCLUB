"""RRClub Portugal: split P5 5/80/5/10, separate charges and transfers.

Read-only by default. NO Stripe transfer unless all of:
 PT_SPLIT_ENABLED=true, PT_SPLIT_LIVE_ENABLED=true,
 PT_SPLIT_AUTO_TRANSFER=true, verified paid P5 EUR checkout,
 and both PT beneficiary Stripe Connect accounts are ready and ID-bound.

Legacy purchases and Pix/BRL are excluded. Transfers != bank payouts.
"""
import asyncio
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, NO_ID, now_iso, require_role
from finance_evidence import connect_account_evidence

router = APIRouter()
VERSION = "pt-p5-fixed-5-80-5-10-v1"


def flag(name):
    return os.environ.get(name, "false").strip().lower() == "true"


def live_enabled():
    return flag("PT_SPLIT_ENABLED") and flag("PT_SPLIT_LIVE_ENABLED")


def automatic():
    return live_enabled() and flag("PT_SPLIT_AUTO_TRANSFER")


def cents(x):
    try:
        d = Decimal(str(x))
        if not d.is_finite():
            raise ValueError("Valor não finito")
        return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Valor financeiro inválido") from exc


def quote(gross_minor):
    """Gross original bill in cents; platform owns Stripe costs."""
    if type(gross_minor) is not int or gross_minor < 100 or gross_minor > 1_000_000:
        raise ValueError("Conta original fora dos limites P5 Portugal")
    discount = int((Decimal(gross_minor) * Decimal("0.05")).quantize(0, rounding=ROUND_HALF_UP))
    received = gross_minor - discount
    partner = int((Decimal(gross_minor) * Decimal("0.80")).quantize(0, rounding=ROUND_HALF_UP))
    creator = int((Decimal(gross_minor) * Decimal("0.05")).quantize(0, rounding=ROUND_HALF_UP))
    platform = received - partner - creator
    if received < 50 or platform < 0 or (partner + creator + platform) != received:
        raise ValueError("Distribuição financeira incompatível")
    return {
        "gross_minor": gross_minor, "discount_minor": discount,
        "payment_minor": received, "partner_minor": partner,
        "influencer_minor": creator, "platform_minor": platform,
        "currency": "eur", "version": VERSION,
        "stripe_fees_borne_by": "platform",
    }


def _stripe_account(account_id, expected_id, role):
    if not account_id or not str(account_id).startswith("acct_"):
        return {"ok": False, "reason": "stripe_account_missing", "role": role}
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        return {"ok": False, "reason": "stripe_key_missing", "role": role}
    try:
        acc = stripe.Account.retrieve(account_id, api_key=key)
    except stripe.error.StripeError:
        return {"ok": False, "reason": "stripe_account_unavailable", "role": role}
    obj = dict(acc)
    metadata = obj.get("metadata") or {}
    bind_name = "partner_id" if role == "partner" else "influencer_id"
    if obj.get("id") != account_id or metadata.get(bind_name) != expected_id:
        return {"ok": False, "reason": "account_id_binding_mismatch", "role": role}
    if str(obj.get("country", "")).upper() != "PT":
        return {"ok": False, "reason": "account_not_portugal", "role": role}
    requirements = obj.get("requirements") or {}
    due = (
        requirements.get("currently_due") or requirements.get("past_due")
        or requirements.get("disabled_reason")
    )
    ok = (
        (obj.get("capabilities") or {}).get("transfers") == "active"
        and obj.get("payouts_enabled") is True
        and not due
    )
    return {
        "ok": bool(ok),
        "reason": "ready" if ok else "connect_onboarding_or_transfers_pending",
        "role": role,
        "account_id": account_id,
        "payouts_enabled": bool(obj.get("payouts_enabled")),
        "transfers_active": (obj.get("capabilities") or {}).get("transfers") == "active",
        "requirements_pending": bool(due),
    }


async def recipients_ready(partner_id, influencer_id):
    """Checks ID association and current receiving state, without creating accounts."""
    if not partner_id or not influencer_id:
        return {"ok": False, "reason": "partner_or_influencer_missing"}
    partner, creator = await asyncio.gather(
        db.partners.find_one({"id": partner_id}, NO_ID),
        db.influencers.find_one({"id": influencer_id}, NO_ID),
    )
    if not partner or not creator:
        return {"ok": False, "reason": "beneficiary_not_found"}
    if str(partner.get("currency") or "eur").lower() != "eur" or str(creator.get("currency") or "eur").lower() != "eur":
        return {"ok": False, "reason": "cross_currency_recipient"}
    partner_acct = partner.get("stripe_account_id")
    creator_acct = creator.get("stripe_account_id")
    if partner_acct and partner_acct == creator_acct:
        return {"ok": False, "reason": "duplicate_connected_account"}
    p, i = await asyncio.gather(
        asyncio.to_thread(_stripe_account, partner_acct, partner_id, "partner"),
        asyncio.to_thread(_stripe_account, creator_acct, influencer_id, "influencer"),
    )
    return {
        "ok": bool(p["ok"] and i["ok"]),
        "partner": p, "influencer": i,
        "reason": "ready" if p["ok"] and i["ok"] else "connect_not_ready",
    }


@router.get("/admin/finance/pt-split/health")
async def pt_health(user: dict = Depends(require_role("admin"))):
    """Read-only; no payments/transfers. Avoid exposing KYC documents."""
    camps = await db.campaigns.find(
        {"status": "Ativa"}, {"_id": 0, "id": 1, "nome": 1, "parceiro_id": 1,
                              "influencer_id": 1, "desconto": 1, "comissao": 1, "currency": 1}
    ).limit(60).to_list(60)
    # No Stripe requests for 60 arbitrary accounts. Lookup per campaign below.
    return {
        "currency": "eur", "rules": {"discount": 5, "partner": 80, "influencer": 5, "rrclub": 10},
        "configuration": {"p5_live_pt_enabled": live_enabled(), "automatic_transfers_enabled": automatic()},
        "campaigns": [
            {"id": x["id"], "name": x.get("nome"), "rule_matches": (
                str(x.get("desconto")) in ("5", "5.0")
                and str(x.get("comissao")) in ("5", "5.0")
                and str(x.get("currency") or "eur").lower() == "eur"
                and bool(x.get("parceiro_id") and x.get("influencer_id"))
            )}
            for x in camps if str(x.get("currency") or "eur").lower() == "eur"
        ],
        "bank_payout_verified": False,
        "note": "Nenhum repasse automatico a transacoes historicas",
    }


@router.get("/admin/finance/pt-split/campaign/{campaign_id}")
async def campaign_health(campaign_id: str, user: dict = Depends(require_role("admin"))):
    campaign = await db.campaigns.find_one({"id": campaign_id}, NO_ID)
    if not campaign:
        raise HTTPException(404, "Campanha não encontrada")
    if (str(campaign.get("currency") or "eur").lower() != "eur"):
        raise HTTPException(409, "Campanha pertence a outra moeda")
    quote_ok = str(campaign.get("desconto")) in ("5", "5.0") and str(campaign.get("comissao")) in ("5", "5.0")
    beneficiaries = await recipients_ready(campaign.get("parceiro_id"), campaign.get("influencer_id"))
    return {
        "campaign_id": campaign_id,
        "rule_matches": quote_ok,
        "receivers": beneficiaries,
        "live_pt_enabled": live_enabled(),
        "automatic_transfer_enabled": automatic(),
        "ready_for_new_p5_live_charge": bool(quote_ok and beneficiaries["ok"] and automatic()),
        "bank_payout_verified": False,
    }


@router.get("/admin/finance/pt-split/quote")
async def quote_preview(gross: Decimal = Query(..., gt=0, le=10000),
                        user: dict = Depends(require_role("admin"))):
    try:
        return quote(cents(gross))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


async def _mark(session_id, status, reason=None):
    update = {"pt_split_status": status, "pt_split_checked_at": now_iso()}
    if reason:
        update["pt_split_reason"] = reason
    await db.payment_transactions.update_one(
        {"session_id": session_id, "split_version": VERSION},
        {"$set": update},
    )


async def settle_new_p5_payment(session_id):
    """Webhook-only opt-in: never process old, manual, Pix or unapproved charges."""
    if not automatic():
        return {"status": "disabled"}
    tx = await db.payment_transactions.find_one(
        {"session_id": session_id, "currency": "eur", "kind": "coupon_pay",
         "split_version": VERSION, "payment_status": "paid"}, NO_ID
    )
    if not tx:
        return {"status": "not_eligible"}
    required = ("p5_charge_id", "partner_id", "influencer_id",
                "partner_destination", "influencer_destination",
                "gross_minor", "amount")
    if any(tx.get(k) is None for k in required):
        await _mark(session_id, "held", "missing_checkout_snapshot")
        return {"status": "held"}
    try:
        financial = quote(int(tx["gross_minor"]))
    except (ValueError, TypeError):
        await _mark(session_id, "held", "invalid_quote")
        return {"status": "held"}
    if cents(tx["amount"]) != financial["payment_minor"]:
        await _mark(session_id, "held", "amount_mismatch")
        return {"status": "held"}
    states = await recipients_ready(tx["partner_id"], tx["influencer_id"])
    if (not states.get("ok")
        or states["partner"].get("account_id") != tx["partner_destination"]
        or states["influencer"].get("account_id") != tx["influencer_destination"]):
        await _mark(session_id, "held", "beneficiary_account_not_ready_or_changed")
        return {"status": "held"}
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    def verify_remote():
        session = stripe.checkout.Session.retrieve(session_id, api_key=key)
        meta = session.get("metadata") or {}
        if (session.get("payment_status") != "paid"
            or session.get("currency") != "eur"
            or session.get("amount_total") != financial["payment_minor"]
            or meta.get("p5_charge_id") != tx["p5_charge_id"]
            or meta.get("partner_id") != tx["partner_id"]
            or meta.get("influencer_id") != tx["influencer_id"]):
            raise ValueError("stripe_checkout_snapshot_mismatch")
        pi = stripe.PaymentIntent.retrieve(session.get("payment_intent"), api_key=key)
        if pi.get("status") != "succeeded" or pi.get("currency") != "eur" or pi.get("amount") != financial["payment_minor"]:
            raise ValueError("payment_intent_mismatch")
        ch_id = pi.get("latest_charge")
        if hasattr(ch_id, "get"):
            ch_id = ch_id.get("id")
        charge = stripe.Charge.retrieve(ch_id, api_key=key) if ch_id else None
        if (not charge or charge.get("paid") is not True or charge.get("currency") != "eur"
            or charge.get("amount") != financial["payment_minor"]
            or charge.get("refunded") or charge.get("disputed")
            or (charge.get("amount_refunded") or 0) > 0
            or charge.get("transfer")):
            raise ValueError("charge_not_safe_for_transfer")
        # Prevent accidentally adding a transfer to an older/different split.
        previous = stripe.Transfer.list(transfer_group=tx["p5_charge_id"], limit=100, api_key=key)
        found = {}
        for transfer in previous.get("data") or []:
            role = (transfer.get("metadata") or {}).get("rrclub_pt_role")
            if (role not in ("partner", "influencer")
                or (transfer.get("metadata") or {}).get("p5_charge_id") != tx["p5_charge_id"]
                or role in found):
                raise ValueError("unknown_or_duplicate_existing_transfer")
            found[role] = transfer
        return ch_id, found
    try:
        charge_id, existing = await asyncio.to_thread(verify_remote)
    except (ValueError, stripe.error.StripeError):
        await _mark(session_id, "held", "stripe_payment_or_transfer_not_verified")
        return {"status": "held"}
    # Retry the same Stripe idempotency key; never use a new key for the same beneficiary.
    for role, amount_field, destination_field in (
        ("partner", "partner_minor", "partner_destination"),
        ("influencer", "influencer_minor", "influencer_destination"),
    ):
        prev = existing.get(role)
        amount, destination = financial[amount_field], tx[destination_field]
        if prev:
            if (prev.get("destination") != destination or prev.get("amount") != amount
                or prev.get("source_transaction") != charge_id
                or prev.get("reversed") or (prev.get("amount_reversed") or 0)):
                await _mark(session_id, "held", "existing_transfer_mismatch_or_reversed")
                return {"status": "held"}
            transfer_id = prev["id"]
        else:
            if tx.get(role + "_transfer_started_at"):
                # A network failure may have created a transfer; never risk
                # retrying after Stripe's idempotency retention window.
                await _mark(session_id, "held", "unknown_prior_transfer_attempt")
                return {"status": "held"}
            await db.payment_transactions.update_one(
                {"session_id": session_id, "split_version": VERSION},
                {"$set": {role + "_transfer_started_at": now_iso()}},
            )
            def create():
                return stripe.Transfer.create(
                    amount=amount, currency="eur", destination=destination,
                    source_transaction=charge_id,
                    transfer_group=tx["p5_charge_id"],
                    metadata={"p5_charge_id": tx["p5_charge_id"],
                              "rrclub_pt_role": role, "pt_split_version": VERSION},
                    idempotency_key=f"rrclub-pt-{tx['p5_charge_id']}-{role}",
                    api_key=key,
                )
            try:
                transfer = await asyncio.to_thread(create)
                transfer_id = transfer["id"]
            except stripe.error.StripeError:
                await _mark(session_id, "held", "transfer_needs_manual_reconciliation")
                return {"status": "held"}
        await db.payment_transactions.update_one(
            {"session_id": session_id, "split_version": VERSION},
            {"$set": {role + "_transfer_id": transfer_id,
                      role + "_transfer_status": "transferred_to_connect"}},
        )
    await _mark(session_id, "transferred_to_connect")
    return {"status": "transferred_to_connect", "bank_payout_verified": False}


async def settle_webhook_safely(session_id):
    try:
        return await settle_new_p5_payment(session_id)
    except Exception:
        # Do not claim a Stripe payment failed after it was charged. Make
        # uncertainty visible and require financial reconciliation.
        await _mark(session_id, "held", "financial_review_required")
        return {"status": "held"}


def _validate_origin(origin):
    configured = {x.strip().rstrip("/") for x in os.environ.get("PAYMENT_ALLOWED_ORIGINS", "").split(",") if x.strip()}
    configured.add(os.environ.get("FRONTEND_URL", "").strip().rstrip("/"))
    origin = str(origin or "").rstrip("/")
    p = urlsplit(origin)
    if (not origin or origin not in configured or p.scheme not in ("https", "http")
        or p.hostname is None or p.username or p.password or p.path not in ("", "/")
        or p.query or p.fragment or (p.scheme == "http" and p.hostname not in ("localhost", "127.0.0.1"))):
        raise HTTPException(400, "Origem não autorizada")
    return origin


@router.post("/influencer/pt/connect/onboard")
async def influencer_connect(body: dict, user: dict = Depends(require_role("influencer"))):
    """Creates/connects an influencer account only on an authenticated user action."""
    creator_id = user.get("influencer_id")
    creator = await db.influencers.find_one({"id": creator_id, "user_id": user["id"]}, NO_ID)
    if not creator or str(creator.get("currency") or "eur").lower() != "eur":
        raise HTTPException(403, "Influenciador Portugal não identificado")
    origin = _validate_origin(body.get("origin_url"))
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(503, "Stripe Portugal não configurado")
    acct_id = creator.get("stripe_account_id")
    if acct_id:
        evidence = await asyncio.to_thread(_stripe_account, acct_id, creator_id, "influencer")
        if evidence["reason"] == "account_id_binding_mismatch":
            raise HTTPException(409, "Conta Connect associada a outro beneficiário")
    else:
        def create():
            return stripe.Account.create(
                type="express", country="PT", email=user["email"],
                capabilities={"transfers": {"requested": True}},
                metadata={"influencer_id": creator_id},
                idempotency_key="rrclub-pt-influencer-" + creator_id,
                api_key=key,
            )
        try:
            acct = await asyncio.to_thread(create)
        except stripe.error.StripeError:
            raise HTTPException(503, "Stripe Connect requer ativação da plataforma")
        acct_id = acct["id"]
        updated = await db.influencers.update_one(
            {"id": creator_id, "user_id": user["id"], "stripe_account_id": {"$in": [None, ""]}},
            {"$set": {"stripe_account_id": acct_id, "stripe_payouts_enabled": False}},
        )
        if not updated.matched_count:
            raise HTTPException(409, "A associação Connect mudou; atualize o painel")
    try:
        link = await asyncio.to_thread(
            stripe.AccountLink.create, account=acct_id,
            type="account_onboarding",
            refresh_url=origin + "/influencer/extrato?connect=refresh",
            return_url=origin + "/influencer/extrato?connect=return",
            api_key=key,
        )
    except stripe.error.StripeError:
        raise HTTPException(503, "Não foi possível abrir a verificação Stripe Connect")
    return {"available": True, "url": link["url"], "account_id": acct_id}


@router.get("/influencer/pt/connect/status")
async def influencer_connect_status(user: dict = Depends(require_role("influencer"))):
    creator_id = user.get("influencer_id")
    creator = await db.influencers.find_one({"id": creator_id, "user_id": user["id"]}, NO_ID)
    if not creator:
        raise HTTPException(403, "Influenciador não identificado")
    info = await asyncio.to_thread(_stripe_account, creator.get("stripe_account_id"), creator_id, "influencer")
    return {
        "connected": bool(creator.get("stripe_account_id")),
        "status_verified": info["reason"] != "stripe_account_unavailable",
        "receiving_ready": bool(info["ok"]),
        "reason": info["reason"],
    }
