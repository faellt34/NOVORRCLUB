#!/usr/bin/env python3
"""Read-only reasons why current RRClub campaigns do not enter P5.

Do not change campaign percentages, status, recipients, Stripe, Pix, or MB WAY.
Prints only campaign codes/IDs and aggregate readiness blockers.
"""
import asyncio
from collections import Counter
from datetime import date
import json
import os
from pathlib import Path
import sys

ROOT = Path("/app") if (Path("/app") / "backend/server.py").is_file() else Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))


def percent_equal(value, target=5):
    try:
        return float(str(value).strip().replace(",", ".")) == float(target)
    except (TypeError, ValueError, OverflowError):
        return False


def check_campaign(campaign, partner_currency=None, today=None):
    """Match real P5 rules; return reasons without changing the campaign."""
    today = today or date.today().isoformat()
    reasons = []
    status = str(campaign.get("status") or "").strip()
    if status != "Ativa":
        reasons.append("status_not_Ativa")
    if not campaign.get("parceiro_id"):
        reasons.append("missing_partner_id")
    if not campaign.get("influencer_id"):
        reasons.append("missing_influencer_id")
    if not percent_equal(campaign.get("desconto")):
        reasons.append("discount_not_5")
    if not percent_equal(campaign.get("comissao")):
        reasons.append("commission_not_5")
    if campaign.get("validade") and str(campaign["validade"])[:10] < today:
        reasons.append("campaign_expired")
    currency = str(campaign.get("currency") or partner_currency or "").strip().lower()
    if currency not in ("brl", "eur"):
        reasons.append("currency_missing_or_unknown")
    return {"currency": currency if currency in ("brl", "eur") else "unknown",
            "status": status or "not_set", "p5_criteria_pass": not reasons,
            "reasons": reasons}


def summarize_campaigns(campaigns, partner_currencies, today=None):
    """Aggregations reflect only the sampled campaign records."""
    groups = Counter()
    causes = Counter()
    examples = []
    p5_by_country = {"brl": 0, "eur": 0}
    legacy_by_country = {"brl": 0, "eur": 0, "unknown": 0}
    for c in campaigns:
        result = check_campaign(c, partner_currencies.get(c.get("parceiro_id")), today)
        groups[result["status"]] += 1
        if result["p5_criteria_pass"]:
            p5_by_country[result["currency"]] += 1
        else:
            legacy_by_country[result["currency"]] += 1
            causes.update(result["reasons"])
            if len(examples) < 12:
                examples.append({
                    "campaign_id": c.get("id"),
                    "coupon": c.get("cupom"),
                    "country": result["currency"],
                    "status": result["status"],
                    "discount_percent": c.get("desconto"),
                    "commission_percent": c.get("comissao"),
                    "reasons": result["reasons"],
                })
    return {
        "campaigns_checked": len(campaigns),
        "status_counts": dict(sorted(groups.items())),
        "p5_eligible_by_country": p5_by_country,
        "not_p5_by_country": legacy_by_country,
        "p5_exclusion_reasons": dict(sorted(causes.items())),
        "non_p5_examples_limited_to_12": examples,
        "unmodified_legacy_campaigns": True,
    }


async def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend/.env", override=False)
    from core import db
    print("RRCLUB P5: campanha por campanha — diagnóstico somente leitura")
    try:
        await asyncio.wait_for(db.command("ping"), timeout=8)
    except Exception as exc:
        print(json.dumps({"database_reachable": False,
                          "error_type": type(exc).__name__}, ensure_ascii=False))
        return
    total = await db.campaigns.count_documents({})
    active = await db.campaigns.count_documents({"status": "Ativa"})
    old_status = await db.campaigns.count_documents({"status": "Ativo"})
    campaigns = await db.campaigns.find(
        {}, {"_id": 0, "id": 1, "cupom": 1, "status": 1,
             "currency": 1, "parceiro_id": 1, "influencer_id": 1,
             "desconto": 1, "comissao": 1, "validade": 1}
    ).sort("_id", 1).limit(1001).to_list(1001)
    partners = await db.partners.find(
        {}, {"_id": 0, "id": 1, "currency": 1}
    ).limit(3000).to_list(3000)
    currency_by_partner = {p.get("id"): p.get("currency") for p in partners}
    report = summarize_campaigns(campaigns[:1000], currency_by_partner)
    report.update({
        "read_only": True,
        "database_name": os.environ.get("DB_NAME") or "NOT_SET",
        "total_campaigns_in_database": total,
        "active_canonical_Ativa": active,
        "active_legacy_Ativo": old_status,
        "sample_truncated": len(campaigns) > 1000,
        "change_count": 0,
        "interpretation": (
            "Somente campanhas com status Ativa, taxas P5 5/5, ambos IDs, "
            "validade atual e moeda correspondente entram no QR P5. "
            "Os restantes cupões continuam no fluxo legado. "
            "Nunca mudar descontos ou comissoes automaticamente."
        ),
    })
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
