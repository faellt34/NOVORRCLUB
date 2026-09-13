from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from core import db, NO_ID, get_current_user, require_role, audit, notify, admin_ids, new_id, now_iso

router = APIRouter()


def since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def totals(reds):
    rev = sum(r["amount"] for r in reds)
    return {"count": len(reds), "revenue": round(rev, 2), "discounts": round(sum(r["discount"] for r in reds), 2),
            "commission": round(sum(r["commission"] for r in reds), 2), "ticket": round(rev / len(reds), 2) if reds else 0}


def trend(cur, prev):
    if not prev:
        return "+100%" if cur else "0%"
    v = (cur - prev) / prev * 100
    return f"{'+' if v >= 0 else ''}{v:.1f}%".replace(".", ",")


def daily_series(reds, days):
    buckets = defaultdict(int)
    for r in reds:
        buckets[r["date"][:10]] += 1
    today = datetime.now(timezone.utc).date()
    step = 1 if days <= 30 else 3
    out = []
    for i in range(days - 1, -1, -step):
        d = today - timedelta(days=i)
        out.append({"date": d.isoformat(), "utilizacoes": sum(buckets.get((d - timedelta(days=k)).isoformat(), 0) for k in range(step))})
    return out


async def enrich_campaigns(camps):
    parts = {p["id"]: p async for p in db.partners.find({}, NO_ID)}
    infs = {i["id"]: i async for i in db.influencers.find({}, NO_ID)}
    for c in camps:
        p = parts.get(c.get("parceiro_id"), {})
        i = infs.get(c.get("influencer_id"), {})
        c["parceiro"] = p.get("nome", c.get("parceiro", "—"))
        c["cidade"] = p.get("cidade", "—")
        c["categoria"] = p.get("categoria", "—")
        c["influencer"] = i.get("nome", "—")
    return camps


@router.get("/dashboard/influencer")
async def influencer_dashboard(period: int = 30, user: dict = Depends(require_role("influencer"))):
    inf_id = user.get("influencer_id")
    reds = await db.redemptions.find({"influencer_id": inf_id, "date": {"$gte": since(period)}}, NO_ID).to_list(20000)
    prev = await db.redemptions.find({"influencer_id": inf_id, "date": {"$gte": since(period * 2), "$lt": since(period)}}, NO_ID).to_list(20000)
    t, tp = totals(reds), totals(prev)
    camps = await enrich_campaigns(await db.campaigns.find({"influencer_id": inf_id}, NO_ID).to_list(500))
    uses = defaultdict(int); rev = defaultdict(float)
    for r in reds:
        uses[r["campaign_id"]] += 1; rev[r["campaign_id"]] += r["amount"]
    for c in camps:
        c["uses"] = uses[c["id"]]; c["revenue"] = round(rev[c["id"]], 2)
    by_partner = defaultdict(lambda: {"uses": 0, "revenue": 0.0})
    for r in reds:
        by_partner[r["partner_id"]]["uses"] += 1; by_partner[r["partner_id"]]["revenue"] += r["amount"]
    parts = {p["id"]: p async for p in db.partners.find({}, NO_ID)}
    top = sorted([{**parts.get(pid, {"id": pid, "nome": "—"}), **v} for pid, v in by_partner.items()], key=lambda x: -x["revenue"])[:5]
    claim_q = {"influencer_id": inf_id, "date": {"$gte": since(period)}}
    claims = await db.coupon_claims.count_documents(claim_q)
    claims_prev = await db.coupon_claims.count_documents({"influencer_id": inf_id, "date": {"$gte": since(period * 2), "$lt": since(period)}})
    claims_by_campaign = defaultdict(int)
    async for cl in db.coupon_claims.find(claim_q, {"campaign_id": 1}):
        claims_by_campaign[cl["campaign_id"]] += 1
    for c in camps:
        c["claims"] = claims_by_campaign[c["id"]]
    active = [c for c in camps if c["status"] == "Ativa"]
    featured = max(active, key=lambda c: c["uses"]) if active else None
    avg_rate = (t["commission"] / t["revenue"] * 100) if t["revenue"] else 10
    return {
        "kpis": {"uses": t["count"], "customers": claims, "revenue": t["revenue"], "commission": t["commission"], "rate": round(avg_rate),
                 "conversion": round(t["count"] / claims * 100, 1) if claims else None,
                 "trend": {"uses": trend(t["count"], tp["count"]), "revenue": trend(t["revenue"], tp["revenue"]), "commission": trend(t["commission"], tp["commission"]), "customers": trend(claims, claims_prev)}},
        "chart": daily_series(reds, period), "topPartners": top, "campaigns": camps, "featured": featured,
    }


@router.get("/dashboard/partner")
async def partner_dashboard(user: dict = Depends(require_role("partner"))):
    pid = user.get("partner_id")
    reds = await db.redemptions.find({"partner_id": pid}, NO_ID).sort("date", -1).to_list(20000)
    cur = [r for r in reds if r["date"] >= since(30)]
    prev = [r for r in reds if since(60) <= r["date"] < since(30)]
    t, tc, tp = totals(reds), totals(cur), totals(prev)
    board = defaultdict(lambda: {"redemptions": 0, "revenue": 0.0, "commission": 0.0})
    for r in reds:
        b = board[r["influencer_id"]]; b["redemptions"] += 1; b["revenue"] += r["amount"]; b["commission"] += r["commission"]
    infs = {i["id"]: i async for i in db.influencers.find({}, NO_ID)}
    leaderboard = sorted([{**infs.get(k, {"id": k, "nome": "—"}), **{kk: round(vv, 2) for kk, vv in v.items()}} for k, v in board.items()], key=lambda x: -x["revenue"])[:5]
    partner = await db.partners.find_one({"id": pid}, NO_ID)
    t["online_paid"] = round(sum(r["amount"] - r["discount"] for r in reds if r.get("paid_online")), 2)
    return {"partner": partner, "totals": t, "trend": {"revenue": trend(tc["revenue"], tp["revenue"]), "count": trend(tc["count"], tp["count"]), "commission": trend(tc["commission"], tp["commission"])},
            "leaderboard": leaderboard, "redemptions": reds[:100]}


@router.get("/dashboard/admin")
async def admin_dashboard(user: dict = Depends(require_role("admin"))):
    reds = await db.redemptions.find({}, NO_ID).to_list(50000)
    cur = [r for r in reds if r["date"] >= since(30)]
    prev = [r for r in reds if since(60) <= r["date"] < since(30)]
    t, tc, tp = totals(reds), totals(cur), totals(prev)
    camps = await enrich_campaigns(await db.campaigns.find({}, NO_ID).sort("validade", -1).to_list(50))
    return {
        "totals": t, "trend": {"revenue": trend(tc["revenue"], tp["revenue"]), "commission": trend(tc["commission"], tp["commission"])},
        "counts": {"influencers": await db.influencers.count_documents({"status": "Ativo"}), "partners": await db.partners.count_documents({"status": "Ativo"}),
                   "campaigns": await db.campaigns.count_documents({"status": "Ativa"}), "users": await db.users.count_documents({})},
        "campaigns": camps[:8], "chart": daily_series(cur, 30),
    }


@router.get("/audit")
async def audit_list(limit: int = 100, user: dict = Depends(require_role("admin"))):
    return await db.audit_log.find({}, NO_ID).sort("date", -1).to_list(limit)


@router.get("/coupons/preview/{code}")
async def preview_coupon(code: str, user: dict = Depends(require_role("partner"))):
    c = await db.campaigns.find_one({"cupom": code.strip().upper(), "parceiro_id": user.get("partner_id")}, NO_ID)
    if not c:
        return None
    inf = await db.influencers.find_one({"id": c.get("influencer_id")}, NO_ID)
    return {**c, "influencer": inf["nome"] if inf else "—"}


class RedeemIn(BaseModel):
    code: str
    amount: float
    idempotency_key: str


@router.post("/redemptions")
async def redeem(body: RedeemIn, user: dict = Depends(require_role("partner"))):
    code = body.code.strip().upper()
    existing = await db.redemptions.find_one({"idempotency_key": body.idempotency_key}, NO_ID)
    if existing:
        return {"record": existing, "duplicate": True}
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor de compra válido.")
    c = await db.campaigns.find_one({"cupom": code, "parceiro_id": user.get("partner_id")}, NO_ID)
    if not c:
        raise HTTPException(status_code=404, detail="Cupom não encontrado para este parceiro.")
    if c["status"] != "Ativa":
        raise HTTPException(status_code=409, detail=f"Cupom {'expirado' if c['status'] == 'Expirada' else 'pausado'} — não pode ser redimido.")
    if c.get("validade") and c["validade"] < datetime.now(timezone.utc).date().isoformat():
        raise HTTPException(status_code=409, detail="Cupom fora da validade — não pode ser redimido.")
    recent = await db.redemptions.find_one({"partner_id": user["partner_id"], "coupon": code, "amount": body.amount, "date": {"$gte": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()}}, NO_ID)
    if recent:
        raise HTTPException(status_code=409, detail="Redenção idêntica registada há menos de 10 segundos — aguarde alguns segundos se for uma venda diferente.")
    inf = await db.influencers.find_one({"id": c.get("influencer_id")}, NO_ID)
    partner = await db.partners.find_one({"id": user["partner_id"]}, NO_ID)
    rate = float(c["comissao"]) / 100
    rec = {"id": new_id("r"), "coupon": code, "campaign_id": c["id"], "campaign": c["nome"], "partner_id": user["partner_id"], "partner": partner["nome"] if partner else user["nome"],
           "influencer_id": c.get("influencer_id"), "influencer": inf["nome"] if inf else "—", "amount": round(body.amount, 2),
           "discount": round(body.amount * float(c["desconto"]) / 100, 2), "commission": round(body.amount * rate, 2), "rate": rate,
           "date": now_iso(), "staff": user["nome"], "idempotency_key": body.idempotency_key}
    try:
        await db.redemptions.insert_one(dict(rec))
    except DuplicateKeyError:
        existing = await db.redemptions.find_one({"idempotency_key": body.idempotency_key}, NO_ID)
        return {"record": existing, "duplicate": True}
    await audit("REDENÇÃO", f"{code} · {rec['amount']:.2f}€ · taxa travada {c['comissao']}% · {rec['partner']}", user, rec["id"])
    inf_user = await db.users.find_one({"influencer_id": c.get("influencer_id")}, {"id": 1}) if inf else None
    await notify(([inf_user["id"]] if inf_user else []) + await admin_ids(), "redencao", "Nova redenção",
                 f"{code} validado em {rec['partner']} · {rec['amount']:.2f}€ · comissão {rec['commission']:.2f}€", "/influencer")
    return {"record": rec, "duplicate": False}


@router.get("/redemptions")
async def list_redemptions(user: dict = Depends(get_current_user)):
    q = {"partner_id": user["partner_id"]} if user["role"] == "partner" else {"influencer_id": user["influencer_id"]} if user["role"] == "influencer" else {}
    return await db.redemptions.find(q, NO_ID).sort("date", -1).to_list(2000)


@router.get("/statements")
async def statements(user: dict = Depends(require_role("influencer"))):
    reds = await db.redemptions.find({"influencer_id": user["influencer_id"]}, NO_ID).to_list(50000)
    paid = {p["month"]: p["paid_at"] async for p in db.payouts.find({"influencer_id": user["influencer_id"]}, NO_ID)}
    months = defaultdict(lambda: defaultdict(lambda: {"uses": 0, "revenue": 0.0, "commission": 0.0}))
    for r in reds:
        m = r["date"][:7]
        line = months[m][(r["campaign"], r["partner"], r["rate"])]
        line["uses"] += 1; line["revenue"] += r["amount"]; line["commission"] += r["commission"]
    out = []
    for m in sorted(months, reverse=True):
        lines = [{"campaign": k[0], "partner": k[1], "rate": k[2], **{kk: round(vv, 2) for kk, vv in v.items()}} for k, v in months[m].items()]
        lines.sort(key=lambda l: -l["revenue"])
        out.append({"id": m, "status": "Pago" if m in paid else "Pendente", "paidAt": paid.get(m), "lines": lines})
    return out


@router.get("/ebooks")
async def ebooks(user: dict = Depends(get_current_user)):
    items = await db.ebooks.find({}, NO_ID).to_list(500)
    sub = await db.subscriptions.find_one({"user_id": user["id"], "status": "active"}, NO_ID)
    owned = {e["ebook_id"] async for e in db.entitlements.find({"user_id": user["id"]}, NO_ID)}
    for e in items:
        e["has_pdf"] = bool(e.get("pdf_path"))
        e["owned"] = e["id"] in owned
        e["unlocked"] = (not e.get("premium")) or user["role"] == "admin" or bool(sub) or e["id"] in owned
        e.pop("pdf_path", None)
    return items


@router.get("/notifications")
async def notifications(user: dict = Depends(get_current_user)):
    items = await db.notifications.find({"user_id": user["id"]}, NO_ID).sort("date", -1).to_list(50)
    return {"items": items, "unread": sum(1 for i in items if not i["lido"])}


@router.post("/notifications/read")
async def read_notifications(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"], "lido": False}, {"$set": {"lido": True}})
    return {"ok": True}


@router.get("/public/coupon/{code}")
async def public_coupon(code: str, request: Request):
    c = await db.campaigns.find_one({"cupom": code.strip().upper()}, NO_ID)
    if not c:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    inf = await db.influencers.find_one({"id": c.get("influencer_id")}, NO_ID) or {}
    ip = request.client.host if request.client else "?"
    ua = request.headers.get("user-agent", "")[:120]
    key = f"{c['cupom']}:{ip}:{ua}"
    recent = await db.coupon_claims.find_one({"key": key, "date": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()}})
    if not recent:
        await db.coupon_claims.insert_one({"id": new_id("cl"), "key": key, "coupon": c["cupom"], "campaign_id": c["id"], "influencer_id": c.get("influencer_id"), "partner_id": c.get("parceiro_id"), "date": now_iso()})
    claims = await db.coupon_claims.count_documents({"campaign_id": c["id"]})
    return {"cupom": c["cupom"], "campanha": c["nome"], "desconto": c["desconto"], "validade": c["validade"], "status": c["status"],
            "parceiro": partner.get("nome", "—"), "categoria": partner.get("categoria", ""), "cidade": partner.get("cidade", ""), "avatar": partner.get("avatar"),
            "influencer": inf.get("nome", "—"), "influencer_handle": inf.get("handle", ""), "influencer_avatar": inf.get("avatar"), "claims": claims}


CITY_COORDS = {"Lisboa": (38.72, -9.14), "Porto": (41.15, -8.61), "Algarve": (37.02, -7.93), "Douro": (41.16, -7.79), "Madrid": (40.42, -3.70), "Barcelona": (41.39, 2.17),
               "Paris": (48.86, 2.35), "Roma": (41.90, 12.50), "Amalfi": (40.63, 14.60), "Dubai": (25.20, 55.27), "Londres": (51.51, -0.13), "Nova Iorque": (40.71, -74.01), "São Paulo": (-23.55, -46.63), "Rio de Janeiro": (-22.91, -43.17)}


@router.get("/public/cities")
async def public_cities():
    out = {}
    async for p in db.partners.find({"status": "Ativo"}, {"cidade": 1, "_id": 0}):
        c = p.get("cidade")
        if c in CITY_COORDS:
            out[c] = out.get(c, 0) + 1
    if not out:
        out = {"Lisboa": 0, "Porto": 0, "Algarve": 0}
    return [{"name": k, "lat": CITY_COORDS[k][0], "lon": CITY_COORDS[k][1], "partners": v} for k, v in out.items()]
