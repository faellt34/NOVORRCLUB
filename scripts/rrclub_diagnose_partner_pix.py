#!/usr/bin/env python3
"""Read-only diagnosis: partner user -> business -> Stripe BR Connect + API 5xx.

No payouts, transfers, Stripe mutations, Mongo writes, keys or full emails printed.
Usage: python3 scripts/rrclub_diagnose_partner_pix.py --name "Paulo Henrique" --account acct_...
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path("/app") if Path("/app/backend/server.py").exists() else Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend/.env", override=False)
from core import db, NO_ID
import stripe


async def diagnose(name, account_id):
    report = {
        "read_only": True, "database": os.environ.get("DB_NAME", "not_set"),
        "stripe_mode": "live" if os.environ.get("PIX_STRIPE_SECRET_KEY", "").startswith("sk_live_") else "not_live",
        "configured_pix_country": os.environ.get("PIX_STRIPE_PLATFORM_COUNTRY", "not_set"),
        "users_matching_name": [], "stripe": {"account_id": account_id},
        "recent_backend_errors": [],
    }
    try:
        await asyncio.wait_for(db.command("ping"), timeout=5)
        report["database_reachable"] = True
    except Exception as exc:
        report["database_reachable"] = False
        report["database_issue"] = type(exc).__name__
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    pattern = "^" + re.escape(name.strip()) + "$"
    users = await db.users.find(
        {"nome": {"$regex": pattern, "$options": "i"}, "role": "partner"}, NO_ID
    ).limit(10).to_list(10)
    company_candidates = await db.partners.find(
        {"nome": {"$regex": "Maraca", "$options": "i"}},
        {"_id": 0, "id": 1, "nome": 1, "currency": 1, "user_id": 1,
         "pix_stripe_account_id": 1},
    ).limit(10).to_list(10)
    report["maraca_candidates"] = [
        {"id": p.get("id"), "name": p.get("nome"),
         "currency": p.get("currency"),
         "has_user_owner": bool(p.get("user_id")),
         "pix_account_matches_expected": p.get("pix_stripe_account_id") == account_id}
        for p in company_candidates
    ]
    related_partner_ids = set()
    for user in users:
        pid = user.get("partner_id")
        related_partner_ids.add(pid)
        partner = await db.partners.find_one({"id": pid}, NO_ID) if pid else None
        report["users_matching_name"].append({
            "user_id": user.get("id"), "role": user.get("role"),
            "user_currency": user.get("currency"),
            "partner_id": pid,
            "partner_found": bool(partner),
            "partner_name": partner.get("nome") if partner else None,
            "partner_currency": partner.get("currency") if partner else None,
            "partner_status": partner.get("status") if partner else None,
            "bidirectional_link_ok": bool(partner and partner.get("user_id") == user.get("id")),
            "stripe_account_in_db": (partner or {}).get("pix_stripe_account_id"),
            "account_id_matches": bool(partner and partner.get("pix_stripe_account_id") == account_id),
        })
    report["candidate_account_used_elsewhere"] = bool(
        await db.partners.find_one(
            {"pix_stripe_account_id": account_id,
             "id": {"$nin": list(related_partner_ids)}}, {"_id": 1}
        ) or await db.influencers.find_one(
            {"pix_stripe_account_id": account_id}, {"_id": 1}
        )
    )

    key = os.environ.get("PIX_STRIPE_SECRET_KEY", "")
    if key.startswith("sk_live_") and os.environ.get("PIX_STRIPE_PLATFORM_COUNTRY") == "BR":
        try:
            platform = await asyncio.to_thread(stripe.Account.retrieve, api_key=key)
            account = await asyncio.to_thread(stripe.Account.retrieve, account_id, api_key=key)
            meta = account.get("metadata") or {}
            requirements = account.get("requirements") or {}
            report["stripe"].update({
                "platform_is_brazil": platform.get("country") == "BR",
                "account_country": account.get("country"),
                "charges_enabled": account.get("charges_enabled"),
                "payouts_enabled": account.get("payouts_enabled"),
                "transfers_active": (account.get("capabilities") or {}).get("transfers") == "active",
                "payout_schedule": (((account.get("settings") or {}).get("payouts") or {}).get("schedule") or {}).get("interval"),
                "requirements_pending": bool(
                    requirements.get("currently_due") or requirements.get("past_due")
                    or requirements.get("disabled_reason")
                ),
                "partner_id_metadata": meta.get("partner_id"),
                "influencer_id_metadata_present": bool(meta.get("influencer_id")),
                "account_email_matches_user": [
                    bool(account.get("email") and user.get("email") and
                         account["email"].casefold() == user["email"].casefold())
                    for user in users
                ],
            })
        except Exception as exc:
            report["stripe"]["verification_error"] = type(exc).__name__
    else:
        report["stripe"]["verification_error"] = "brazil_live_key_not_configured"

    try:
        recent = datetime.now(timezone.utc) - timedelta(hours=24)
        entries = await db.system_logs.find(
            {"origem": "http", "nivel": "error", "ts": {"$gte": recent}},
            {"_id": 0, "caminho": 1, "status": 1, "timestamp": 1},
        ).sort("ts", -1).limit(15).to_list(15)
        report["recent_backend_errors"] = entries
    except Exception:
        report["recent_backend_errors"] = [{"diagnostic": "logs_not_accessible"}]
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print("CONCLUSAO: este diagnostico NAO corrige ou vincula IDs e NAO prova a titularidade.")
    print("Erro Cloudflare 520 pode ocorrer fora da API, sem registo HTTP na aplicacao.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Paulo Henrique")
    parser.add_argument("--account", required=True, help="Stripe Connect acct_... brasileiro")
    args = parser.parse_args()
    if not re.fullmatch(r"acct_[A-Za-z0-9]{10,40}", args.account):
        parser.error("Use um Stripe acct_ valido")
    asyncio.run(diagnose(args.name, args.account))

if __name__ == "__main__":
    main()
