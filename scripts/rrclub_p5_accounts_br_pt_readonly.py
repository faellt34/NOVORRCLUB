#!/usr/bin/env python3
"""RRClub P5: one read-only BR/Portugal reconciliation report for the deployed DB.

No Stripe account edits, no metadata claims, no DB mutation, no payments, no deploy.
Uses exact account IDs as lookup keys; labels/names/emails are NOT identity proof.
Prints no tokens, emails, passwords, KYC, IBANs, or payment secrets.
Run from /app with the backend's configured Python interpreter.
"""
import asyncio
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path("/app") if (Path("/app") / "backend/server.py").is_file() else Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend/.env", override=False)
from core import db, NO_ID
import stripe

PT_PLATFORM = "acct_1UIZ90CZnwrqCuCt"
BR_PLATFORM = "acct_1URXWqEKAxcuX59L"
KNOWN = (
    ("BR", "Paulo/Maraca — Conta BR", "acct_1URwjTEKs764BXlZ",
     "PIX_STRIPE_SECRET_KEY", BR_PLATFORM, "BR", "pix_stripe_account_id"),
    ("PT", "Conta PT-01", "acct_1UIajlE123roTruk",
     "STRIPE_SECRET_KEY", PT_PLATFORM, "PT", "stripe_account_id"),
    ("PT", "Conta PT-02", "acct_1UIacdCy6KhbVjNX",
     "STRIPE_SECRET_KEY", PT_PLATFORM, "PT", "stripe_account_id"),
)


def verified_financial_capability(account, expected_country):
    """Financial readiness is different from owner/bank verification."""
    if not account:
        return False
    needs = account.get("requirements") or {}
    return (
        account.get("country") == expected_country
        and account.get("payouts_enabled") is True
        and (account.get("capabilities") or {}).get("transfers") == "active"
        and not (needs.get("currently_due") or needs.get("past_due")
                 or needs.get("disabled_reason"))
    )


def exact_metadata_binding(account, db_entity, account_id, id_field, role):
    """Both Stripe metadata and the matching DB record must name the same ID."""
    if not account or not db_entity or role not in ("partner", "influencer"):
        return False
    role_key = "partner_id" if role == "partner" else "influencer_id"
    other_key = "influencer_id" if role == "partner" else "partner_id"
    metadata = account.get("metadata") or {}
    return bool(
        account.get("id") == account_id
        and db_entity.get("id")
        and db_entity.get(id_field) == account_id
        and metadata.get(role_key) == db_entity["id"]
        and not metadata.get(other_key)
    )


def p5_policy_campaign(c):
    try:
        return (float(c.get("desconto", -1)) == 5
                and float(c.get("comissao", -1)) == 5
                and bool(c.get("parceiro_id") and c.get("influencer_id")))
    except (ValueError, TypeError):
        return False


async def get_platform_key_health(key_env, platform_id, expected_country):
    key = os.environ.get(key_env, "")
    if not key.startswith(("sk_live_", "rk_live_")):
        return {"status": "live_key_not_configured", "valid": False}
    try:
        remote = await asyncio.wait_for(
            asyncio.to_thread(stripe.Account.retrieve, api_key=key), timeout=15)
        good = (remote.get("id") == platform_id
                and remote.get("country") == expected_country
                and remote.get("charges_enabled") is True)
        return {"status": "verified_correct_live_platform" if good else "WRONG_STRIPE_PLATFORM",
                "valid": good}
    except Exception as exc:
        return {"status": "platform_check_failed_" + type(exc).__name__, "valid": False}


async def get_known_account(account_id, key, platform_ok):
    if not platform_ok:
        return None, "not_checked_wrong_platform_or_key"
    try:
        found = await asyncio.wait_for(
            asyncio.to_thread(stripe.Account.retrieve, account_id, api_key=key),
            timeout=15,
        )
        return dict(found), "retrieved"
    except Exception as exc:
        return None, "read_failed_" + type(exc).__name__


async def related_records(collection, field, account_id):
    return await collection.find(
        {field: account_id},
        {"_id": 0, "id": 1, "nome": 1, "currency": 1, "status": 1,
         "user_id": 1, field: 1},
    ).limit(5).to_list(5)


async def account_report(item, account, lookup_status):
    region, alias, aid, _, _, country, field = item
    partners, influencers = await asyncio.gather(
        related_records(db.partners, field, aid),
        related_records(db.influencers, field, aid),
    )
    correct_role = None
    confirmed = False
    if len(partners) == 1 and not influencers:
        correct_role = "partner"
        confirmed = exact_metadata_binding(account, partners[0], aid, field, "partner")
    elif len(influencers) == 1 and not partners:
        correct_role = "influencer"
        confirmed = exact_metadata_binding(account, influencers[0], aid, field, "influencer")
    financial = verified_financial_capability(account, country)
    result = {
        "region": region, "alias": alias, "account_id": aid,
        "stripe_lookup_status": lookup_status,
        "stripe_financially_capable": financial,
        "stripe_metadata_owner_present": bool(
            (account or {}).get("metadata", {}).get("partner_id")
            or (account or {}).get("metadata", {}).get("influencer_id")),
        "database_partner_candidates": [
            {"id": x.get("id"), "name": x.get("nome"),
             "currency": x.get("currency"), "status": x.get("status")}
            for x in partners
        ],
        "database_influencer_candidates": [
            {"id": x.get("id"), "name": x.get("nome"),
             "currency": x.get("currency"), "status": x.get("status")}
            for x in influencers
        ],
        "candidate_role": correct_role or "unassigned_or_conflicting",
        "beneficiary_binding_verified": confirmed,
        "eligible_for_transfer": bool(confirmed and financial),
        "reason": (
            "verified" if confirmed and financial else
            "financial_requirements_pending" if confirmed and not financial else
            "database_record_not_found" if not partners and not influencers else
            "conflicting_database_records" if len(partners) + len(influencers) != 1 else
            "stripe_metadata_owner_not_verified"
        ),
        "alias_is_not_identity_proof": True,
    }
    return result


async def paulo_report():
    matches = await db.users.find(
        {"role": "partner", "nome": {"$regex": r"Paulo\s+Henrique", "$options": "i"}},
        {"_id": 0, "id": 1, "nome": 1, "partner_id": 1}
    ).limit(10).to_list(10)
    results = []
    for user in matches:
        pid = user.get("partner_id")
        partner = await db.partners.find_one({"id": pid}, NO_ID) if pid else None
        results.append({
            "user_id": user.get("id"), "name": user.get("nome"),
            "linked_partner_id": pid,
            "partner_record_found": bool(partner),
            "partner_name": partner.get("nome") if partner else None,
            "partner_country_currency": (partner or {}).get("currency"),
            "partner_user_link_exact": bool(
                partner and partner.get("user_id") == user.get("id")),
            "br_stripe_account_match": bool(
                partner and partner.get("pix_stripe_account_id") == "acct_1URwjTEKs764BXlZ"),
        })
    return results


async def campaign_summary(accounts):
    """Only evaluate campaigns touching one of the three named accounts.

    Other campaigns are not classified or blocked by this report.
    """
    region_accounts = {
        "brl": {a["account_id"]: a for a in accounts if a["region"] == "BR"},
        "eur": {a["account_id"]: a for a in accounts if a["region"] == "PT"},
    }
    records = await db.campaigns.find(
        {"status": "Ativa"},
        {"_id": 0, "id": 1, "cupom": 1, "nome": 1, "currency": 1,
         "parceiro_id": 1, "influencer_id": 1, "desconto": 1, "comissao": 1}
    ).limit(1001).to_list(1001)
    counts = {"active_campaigns_scanned": min(len(records), 1000),
              "truncated": len(records) > 1000,
              "p5_campaigns_by_currency": {"eur": 0, "brl": 0},
              "matching_known_account_campaigns": [],
              "unrelated_campaigns_not_decided": True}
    for campaign in records[:1000]:
        if not p5_policy_campaign(campaign):
            continue
        currency = str(campaign.get("currency") or "eur").lower()
        if currency not in ("eur", "brl"):
            continue
        counts["p5_campaigns_by_currency"][currency] += 1
        pid, iid = campaign["parceiro_id"], campaign["influencer_id"]
        partner, influencer = await asyncio.gather(
            db.partners.find_one({"id": pid}, NO_ID),
            db.influencers.find_one({"id": iid}, NO_ID),
        )
        field = "pix_stripe_account_id" if currency == "brl" else "stripe_account_id"
        p_acct = (partner or {}).get(field)
        i_acct = (influencer or {}).get(field)
        relevant = p_acct in region_accounts[currency] or i_acct in region_accounts[currency]
        if not relevant:
            continue
        pstate = region_accounts[currency].get(p_acct)
        istate = region_accounts[currency].get(i_acct)
        ready = bool(
            pstate and istate
            and pstate["eligible_for_transfer"] and pstate["candidate_role"] == "partner"
            and istate["eligible_for_transfer"] and istate["candidate_role"] == "influencer"
            and p_acct != i_acct
            and str((partner or {}).get("currency") or currency).lower() == currency
            and str((influencer or {}).get("currency") or currency).lower() == currency
        )
        counts["matching_known_account_campaigns"].append({
            "campaign_id": campaign.get("id"), "coupon": campaign.get("cupom"),
            "currency": currency, "partner_account": p_acct,
            "influencer_account": i_acct,
            "ready_by_known_account_evidence": ready,
            "needs_additional_recipient_checks": True,
        })
    return counts


async def main():
    report = {
        "purpose": "RRClub BR/PT P5 association evidence, read-only",
        "read_only": True, "changes_to_stripe_or_database": 0,
        "database_name": os.environ.get("DB_NAME") or "NOT_SET",
        "p5_flags": {
            x: os.environ.get(x, "not_set").lower()
            for x in ("P5_ENABLED", "P5_BRL_ENABLED", "P5_EUR_ENABLED",
                      "PIX_ENABLED", "PT_SPLIT_ENABLED", "PT_SPLIT_LIVE_ENABLED",
                      "PT_SPLIT_AUTO_TRANSFER")
        },
    }
    try:
        await asyncio.wait_for(db.command("ping"), timeout=8)
        report["db"] = {"reachable": True}
        for collection in ("users", "partners", "influencers", "campaigns"):
            report["db"][collection] = await db[collection].count_documents({})
    except Exception as exc:
        report["db"] = {"reachable": False, "error_type": type(exc).__name__}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    platforms = {}
    for region, _, aid, key_name, platform_id, country, _ in KNOWN:
        if region not in platforms:
            platforms[region] = await get_platform_key_health(
                key_name, platform_id, country)
    report["platforms"] = platforms
    accounts = []
    for row in KNOWN:
        region, _, aid, key_name, _, _, _ = row
        remote, status = await get_known_account(
            aid, os.environ.get(key_name, ""), platforms[region]["valid"])
        accounts.append(await account_report(row, remote, status))
    report["known_accounts"] = accounts
    report["paulo_partner_link"] = await paulo_report()
    report["campaigns"] = await campaign_summary(accounts)
    report["limitations"] = [
        "Metadata vazio nao prova titularidade, mesmo que email coincida.",
        "Nenhuma conta pendente de utilizador bloqueia campanhas nao relacionadas.",
        "Este relatorio NAO ativa split, cria contas ou faz transferencias.",
        "Uma campanha marcada pronta exige confirmacao do fluxo Stripe/webhook antes de dinheiro real.",
    ]
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
