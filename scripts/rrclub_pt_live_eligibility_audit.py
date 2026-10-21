#!/usr/bin/env python3
"""Read-only RRClub Portugal P5 recipient and €1 quotation audit."""
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend/.env", override=False)
from core import db, NO_ID
from pt_split import recipients_ready, quote, automatic, live_enabled
import stripe
import os

def p5_eligible(c):
    try:
        return (
            float(c.get("desconto", -1)) == 5
            and float(c.get("comissao", -1)) == 5
            and bool(c.get("parceiro_id") and c.get("influencer_id"))
            and str(c.get("currency") or "eur").lower() == "eur"
        )
    except (ValueError, TypeError):
        return False

async def main():
    records = await db.campaigns.find({"status": "Ativa"}, NO_ID).limit(1000).to_list(1000)
    aliases = {
        "acct_1UIajlE123roTruk": "Conta PT-01",
        "acct_1UIacdCy6KhbVjNX": "Conta PT-02",
    }
    connected_candidates = []
    stripe_context = "unverified"
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    try:
        platform = await asyncio.to_thread(stripe.Account.retrieve, api_key=key)
        stripe_context = ("verified_live_portugal"
                          if platform.get("id") == "acct_1UIZ90CZnwrqCuCt"
                          else "wrong_stripe_account")
    except Exception as exc:
        stripe_context = "lookup_failed_" + type(exc).__name__
    for ident, label in aliases.items():
        item = {"label": label, "account_id": ident, "status": "not_checked",
                "partner_db_record": None, "influencer_db_record": None,
                "partner_binding_verified": False, "influencer_binding_verified": False}
        if stripe_context == "verified_live_portugal":
            try:
                remote = await asyncio.to_thread(stripe.Account.retrieve, ident, api_key=key)
                req = remote.get("requirements") or {}
                item["status"] = "stripe_ready" if (
                    remote.get("country") == "PT"
                    and remote.get("payouts_enabled") is True
                    and (remote.get("capabilities") or {}).get("transfers") == "active"
                    and not (req.get("currently_due") or req.get("past_due")
                             or req.get("disabled_reason"))) else "stripe_requirements_pending"
                db_partner, db_influencer = await asyncio.gather(
                    db.partners.find_one({"stripe_account_id": ident}, NO_ID),
                    db.influencers.find_one({"stripe_account_id": ident}, NO_ID)
                )
                meta = remote.get("metadata") or {}
                if db_partner:
                    item["partner_db_record"] = {
                        "id": db_partner.get("id"), "name": db_partner.get("nome")}
                    item["partner_binding_verified"] = (
                        not db_influencer and meta.get("partner_id") == db_partner.get("id"))
                if db_influencer:
                    item["influencer_db_record"] = {
                        "id": db_influencer.get("id"), "name": db_influencer.get("nome")}
                    item["influencer_binding_verified"] = (
                        not db_partner and meta.get("influencer_id") == db_influencer.get("id"))
            except Exception as exc:
                item["status"] = "lookup_failed_" + type(exc).__name__
        connected_candidates.append(item)
    checked = []
    for campaign in records:
        if not p5_eligible(campaign):
            continue
        try:
            receiving = await recipients_ready(
                campaign["parceiro_id"], campaign["influencer_id"]
            )
        except Exception:
            receiving = {"ok": False, "reason": "stripe_validation_unavailable"}
        checked.append({
            "coupon": campaign.get("cupom"),
            "campaign_id": campaign.get("id"),
            "partner_id": campaign.get("parceiro_id"),
            "influencer_id": campaign.get("influencer_id"),
            "ready_for_live_split": bool(receiving.get("ok")),
            "reason": receiving.get("reason"),
            "partner": {
                "account_id": (receiving.get("partner") or {}).get("account_id"),
                "reason": (receiving.get("partner") or {}).get("reason")
            },
            "influencer": {
                "account_id": (receiving.get("influencer") or {}).get("account_id"),
                "reason": (receiving.get("influencer") or {}).get("reason")
            }
        })
    print(json.dumps({
        "read_only": True, "payment_created": False, "transfers_created": False,
        "currency": "eur", "stripe_live_split_enabled": live_enabled(),
        "automatic_transfer_enabled": automatic(),
        "one_euro_bill_quote_minor": quote(100),
        "connected_candidates": connected_candidates,
        "stripe_context": stripe_context,
        "database_name": os.environ.get("DB_NAME") or "not_set",
        "active_campaigns_in_db": len(records),
        "eligible_campaigns": [c for c in checked if c["ready_for_live_split"]],
        "blocked_campaigns": [c for c in checked if not c["ready_for_live_split"]],
        "note": "Conta tecnicamente apta nao comprova titularidade. Associar por ID exato na Stripe e base."
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
