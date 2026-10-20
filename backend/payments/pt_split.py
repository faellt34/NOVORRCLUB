"""RRClub Portugal sandbox-only separate-charges-and-transfers P5 settlement.

STRICT OPT-IN: enabled only by PT_SPLIT_V2_ENABLED=true AND sk_test_ PT key.
NO production activation. Amounts derive from original gross charge:
5% discount, 80% partner, 5% influencer, 10% residual platform BEFORE
provider fees. Requires both verified Stripe Connect PT recipients.
"""
import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
import stripe
from payments.stripe_normalize import stripe_payload


def enabled():
    key = os.getenv("STRIPE_SECRET_KEY", "")
    return os.getenv("PT_SPLIT_V2_ENABLED", "").lower() == "true" and key.startswith("sk_test_") and len(key) >= 20


def requested():
    return os.getenv("PT_SPLIT_V2_ENABLED", "").lower() == "true"


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def quote(gross, discount=5, commission=5):
    amount = cents(gross)
    if amount < 100 or amount > 1000000 or discount != 5 or commission != 5:
        raise HTTPException(409, "O split PT experimental exige P5 fixo e conta de 1€ a 10.000€.")
    net = int((Decimal(amount) * Decimal("0.95")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    partner = int((Decimal(amount) * Decimal("0.80")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    influencer = int((Decimal(amount) * Decimal("0.05")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    platform = net - partner - influencer
    if min(net, partner, influencer, platform) <= 0:
        raise HTTPException(409, "Os montantes do split não são válidos.")
    return {"gross_cents": amount, "net_cents": net, "partner_cents": partner,
            "influencer_cents": influencer, "platform_cents": platform}


async def provider(operation, *args, **params):
    """Real Stripe TEST client. Replace with a mock in offline tests."""
    if not enabled():
        raise HTTPException(503, "Split Portugal disponível só com chave de teste sk_test_.")
    def call():
        client = stripe.StripeClient(os.environ["STRIPE_SECRET_KEY"], max_network_retries=0)
        endpoint = client.v1
        for part in operation.split("."):
            endpoint = getattr(endpoint, part)
        options = {}
        key = params.pop("idempotency_key", None)
        if key:
            options["idempotency_key"] = key
        return stripe_payload(endpoint(*args, params=params, options=options))
    try:
        return await asyncio.wait_for(asyncio.to_thread(call), timeout=25)
    except (stripe.StripeError, asyncio.TimeoutError) as exc:
        raise HTTPException(503, "Stripe Portugal TEST temporariamente indisponível.") from exc


async def verify(partner, influencer):
    if not enabled():
        raise HTTPException(503, "Não é permitido um split experimental em contas live.")
    if not partner or not influencer or partner.get("status") != "Ativo" or influencer.get("status") != "Ativo":
        raise HTTPException(409, "Parceiro e influencer devem estar aprovados.")
    for role, entity in (("partner", partner), ("influencer", influencer)):
        account_id = entity.get("stripe_account_id")
        if not account_id or not account_id.startswith("acct_"):
            raise HTTPException(409, f"Connect PT incompleto: {role}.")
        a = await provider("accounts.retrieve", account_id)
        metadata = a.get("metadata") or {}
        account_owner = metadata.get("partner_id") if role == "partner" else metadata.get("influencer_id")
        if (a.get("country") != "PT"
            or a.get("details_submitted") is not True
            or a.get("payouts_enabled") is not True
            or (a.get("capabilities") or {}).get("transfers") != "active"
            or account_owner != entity.get("id")
            or (a.get("requirements") or {}).get("disabled_reason")
            or (a.get("requirements") or {}).get("currently_due")):
            raise HTTPException(409, f"Connect PT ainda não habilitado: {role}.")
    return True


async def settle(transaction, database):
    """Transfers each leg exactly once; partial failures are retryable."""
    if transaction.get("split_mode") != "pt_separate_v2" or not enabled():
        raise HTTPException(503, "Split PT test não autorizado.")
    tx = await database.payment_transactions.find_one({"id": transaction["id"]})
    if not tx or tx.get("payment_status") != "paid" or not tx.get("redemption_id"):
        raise HTTPException(503, "A venda ainda não foi confirmada.")
    if tx.get("dispute_hold") or tx.get("refunded_cents"):
        await database.payment_transactions.update_one({"id":tx["id"]},{"$set":{"split_status":"held"}})
        return
    intent = await provider("payment_intents.retrieve", tx.get("stripe_payment_intent_id"))
    charge = intent.get("latest_charge")
    if (not charge or intent.get("status") != "succeeded" or intent.get("currency") != "eur"
            or intent.get("amount_received") != tx["net_cents"]):
        raise HTTPException(503, "Pagamento em euros ainda não reconciliado.")
    for role in ("partner", "influencer"):
        latest = await database.payment_transactions.find_one({"id":tx["id"]})
        if latest.get(role+"_transfer_id"):
            continue
        if latest.get("dispute_hold") or latest.get("refunded_cents"):
            await database.payment_transactions.update_one({"id":tx["id"]},{"$set":{"split_status":"held"}})
            return
        # Idempotency keys persist across retries, even if DB failed to
        # record a successful Stripe transfer. Never create a second transfer.
        transfer = await provider("transfers.create",
            amount=latest[role+"_cents"], currency="eur",
            destination=latest[role+"_destination"],
            source_transaction=charge, transfer_group=tx["id"],
            metadata={"rrclub_transaction":tx["id"],"recipient":role},
            idempotency_key=tx["id"]+"-pt-v2-"+role)
        await database.payment_transactions.update_one(
            {"id":tx["id"]},{"$set":{role+"_transfer_id":transfer["id"],
                                  role+"_transfer_status":"completed","split_status":"pending"}})
    await database.payment_transactions.update_one({"id":tx["id"]},{"$set":{"split_status":"completed"}})


async def reverse(transaction, database, refunded_cents):
    """Cumulative refund reversal; never reverse more than transferred."""
    if transaction.get("split_mode") != "pt_separate_v2" or not enabled():
        raise HTTPException(503, "Reversão PT TEST não autorizada.")
    tx = await database.payment_transactions.find_one({"id":transaction["id"]})
    if tx is None or not isinstance(refunded_cents, int) or not 0 <= refunded_cents <= tx["net_cents"]:
        raise HTTPException(409,"Valor de reembolso PT inválido.")
    await database.payment_transactions.update_one(
        {"id":tx["id"]}, {"$max":{"refunded_cents":refunded_cents},
                          "$set":{"split_status":"held","manual_payout_blocked":True}})
    latest = await database.payment_transactions.find_one({"id":tx["id"]})
    cumulative = latest.get("refunded_cents", 0)
    for role in ("partner", "influencer"):
        transfer_id = latest.get(role+"_transfer_id")
        if not transfer_id:
            continue
        target = int((Decimal(tx[role+"_cents"]) * Decimal(cumulative) / Decimal(tx["net_cents"])).quantize(Decimal("1"),rounding=ROUND_HALF_UP))
        remote = await provider("transfers.retrieve", transfer_id)
        already = remote.get("amount_reversed", 0)
        if target > already:
            await provider("transfers.reversals.create", transfer_id,
                amount=target-already,
                idempotency_key=tx["id"]+"-pt-v2-"+role+"-refund-"+str(target))
    await database.payment_transactions.update_one({"id":tx["id"]},{"$set":{"reversal_status":"completed"}})
