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
        "eligible_campaigns": [c for c in checked if c["ready_for_live_split"]],
        "blocked_campaigns": [c for c in checked if not c["ready_for_live_split"]],
        "note": "Conta tecnicamente apta nao comprova titularidade. Associar por ID exato na Stripe e base."
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
