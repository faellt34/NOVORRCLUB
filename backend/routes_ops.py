import secrets
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, require_role, audit, notify, new_id, now_iso, hash_password

router = APIRouter()


@router.get("/admin/payouts")
async def payouts_overview(user: dict = Depends(require_role("admin"))):
    reds = await db.redemptions.find({}, {"influencer_id": 1, "influencer": 1, "date": 1, "commission": 1, "_id": 0}).to_list(100000)
    agg = defaultdict(lambda: {"commission": 0.0, "count": 0})
    names = {}
    for r in reds:
        k = (r["influencer_id"], r["date"][:7])
        agg[k]["commission"] += r["commission"]; agg[k]["count"] += 1
        names[r["influencer_id"]] = r["influencer"]
    paid = {(p["influencer_id"], p["month"]): p async for p in db.payouts.find({}, NO_ID)}
    rows = []
    for (inf, month), v in agg.items():
        p = paid.get((inf, month))
        rows.append({"influencer_id": inf, "influencer": names[inf], "month": month, "commission": round(v["commission"], 2), "count": v["count"],
                     "status": "Pago" if p else "Pendente", "paid_at": p["paid_at"] if p else None, "note": p.get("note") if p else None})
    rows.sort(key=lambda r: (r["month"], r["influencer"]), reverse=True)
    return rows


class PayoutIn(BaseModel):
    influencer_id: str
    month: str
    note: Optional[str] = ""


@router.post("/admin/payouts")
async def mark_paid(body: PayoutIn, user: dict = Depends(require_role("admin"))):
    if await db.payouts.find_one({"influencer_id": body.influencer_id, "month": body.month}):
        raise HTTPException(status_code=409, detail="Este mês já está marcado como pago")
    inf = await db.influencers.find_one({"id": body.influencer_id}, NO_ID)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer não encontrado")
    total = sum([r["commission"] async for r in db.redemptions.find({"influencer_id": body.influencer_id, "date": {"$regex": f"^{body.month}"}}, {"commission": 1})])
    doc = {"id": new_id("pay"), "influencer_id": body.influencer_id, "month": body.month, "paid_at": datetime.now(timezone.utc).date().isoformat(), "amount": round(total, 2), "note": body.note, "by": user["nome"]}
    await db.payouts.insert_one(dict(doc))
    await audit("PAGAMENTO", f"Extrato {body.month} de {inf['nome']} marcado como pago · {total:.2f}€", user, doc["id"])
    inf_user = await db.users.find_one({"influencer_id": body.influencer_id}, {"id": 1})
    if inf_user:
        await notify([inf_user["id"]], "pagamento", "Comissão paga 💸", f"O extrato de {body.month} ({total:.2f}€) foi marcado como pago em {doc['paid_at']}.", "/influencer/extrato")
    return doc


@router.delete("/admin/payouts/{influencer_id}/{month}")
async def unmark_paid(influencer_id: str, month: str, user: dict = Depends(require_role("admin"))):
    res = await db.payouts.delete_one({"influencer_id": influencer_id, "month": month})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    await audit("PAGAMENTO", f"Extrato {month} de {influencer_id} revertido para pendente", user, f"{influencer_id}/{month}")
    return {"ok": True}


class ForgotIn(BaseModel):
    email: str


@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email}, NO_ID)
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"id": new_id("prt"), "token": token, "user_id": user["id"], "email": email, "nome": user["nome"],
                                                   "created_at": now_iso(), "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(), "used": False})
        await audit("RECUPERAÇÃO", f"Pedido de recuperação de palavra-passe · {email}", user, token[:8])
        admins = [u["id"] async for u in db.users.find({"role": "admin"}, {"id": 1})]
        await notify(admins, "reset", "Pedido de recuperação de acesso", f"{user['nome']} ({email}) pediu para redefinir a palavra-passe. Envie-lhe o link no painel.", "/admin")
    return {"ok": True, "message": "Se o email existir, o pedido foi registado. O administrador irá enviar-lhe o link de recuperação."}


@router.get("/admin/reset-requests")
async def reset_requests(user: dict = Depends(require_role("admin"))):
    now = now_iso()
    return await db.password_reset_tokens.find({"used": False, "expires_at": {"$gt": now}}, NO_ID).sort("created_at", -1).to_list(100)


class ResetIn(BaseModel):
    token: str
    password: str


@router.get("/auth/reset-password/{token}")
async def reset_check(token: str):
    t = await db.password_reset_tokens.find_one({"token": token}, NO_ID)
    if not t or t["used"] or t["expires_at"] < now_iso():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    return {"email": t["email"], "nome": t["nome"]}


@router.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    t = await db.password_reset_tokens.find_one({"token": body.token}, NO_ID)
    if not t or t["used"] or t["expires_at"] < now_iso():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="A palavra-passe deve ter pelo menos 6 caracteres")
    await db.users.update_one({"id": t["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True, "used_at": now_iso()}})
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{t['email']}$"}})
    await audit("RECUPERAÇÃO", f"Palavra-passe redefinida · {t['email']}", {"id": t["user_id"], "nome": t["nome"]}, body.token[:8])
    return {"ok": True}
