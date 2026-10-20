"""P5 Brasil: preparação de cobrança após leitura de QR.
Integração: incluir router no servidor e vincular token privado da sessão do seguidor.
Não ativa cobranças sem integração explícita; evita contar scan como pagamento.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core import db, NO_ID, get_current_user, require_role, new_id, now_iso

router = APIRouter()

def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

class PrepareCharge(BaseModel):
    code: str
    gross_amount: Decimal = Field(gt=0, le=10000)
    idempotency_key: str = Field(min_length=12, max_length=128)
    follower_session_token: str = Field(min_length=24)

@router.post("/partner/p5/charges")
async def prepare_charge(body: PrepareCharge, user: dict = Depends(require_role("partner"))):
    code = body.code.strip().upper()
    c = await db.campaigns.find_one({"cupom": code, "parceiro_id": user["partner_id"]}, NO_ID)
    if not c or c.get("status") != "Ativa":
        raise HTTPException(404, "Cupão não encontrado ou inativo para este parceiro")
    if c.get("validade") and c["validade"] < datetime.now(timezone.utc).date().isoformat():
        raise HTTPException(409, "Cupão expirado")
    # A sessão deve ser emitida e validada pelo backend de claims, não pelo QR público.
    claim = await db.coupon_claims.find_one({
        "campaign_id": c["id"], "session_token": body.follower_session_token
    }, NO_ID)
    if not claim:
        raise HTTPException(403, "Sessão do seguidor não associada ao cupão")
    existing = await db.p5_charges.find_one({"partner_id": user["partner_id"], "idempotency_key": body.idempotency_key}, NO_ID)
    if existing:
        if existing["coupon"] != code or existing["session_token"] != body.follower_session_token or existing["gross_minor"] != cents(body.gross_amount):
            raise HTTPException(409, "Chave de idempotência reutilizada com dados diferentes")
        return {"charge_id": existing["id"], "status": existing["status"], "duplicate": True}
    gross = cents(body.gross_amount)
    discount_pct = Decimal(str(c["desconto"]))
    if not (Decimal("0") <= discount_pct < Decimal("100")):
        raise HTTPException(409, "Desconto inválido")
    discount = int((Decimal(gross) * discount_pct / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    net = gross - discount
    if net < 50:
        raise HTTPException(400, "Valor após desconto demasiado baixo")
    record = {
        "id": new_id("p5"), "campaign_id": c["id"], "coupon": code,
        "partner_id": user["partner_id"], "claim_id": claim["id"],
        "session_token": body.follower_session_token, "currency": "brl",
        "gross_minor": gross, "discount_minor": discount, "net_minor": net,
        "status": "pending", "idempotency_key": body.idempotency_key,
        "created_at": now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
        "checkout_session_id": None,
    }
    # Em produção criar índice único (partner_id, idempotency_key) na coleção p5_charges.
    try:
        await db.p5_charges.insert_one(record)
    except Exception:
        existing = await db.p5_charges.find_one({"partner_id": user["partner_id"], "idempotency_key": body.idempotency_key}, NO_ID)
        if existing:
            return {"charge_id": existing["id"], "status": existing["status"], "duplicate": True}
        raise
    return {"charge_id": record["id"], "status": "pending", "currency": "brl",
            "gross_minor": gross, "discount_minor": discount, "net_minor": net}

@router.get("/public/p5/charges/current")
async def current_charge(code: str, session_token: str):
    c = await db.campaigns.find_one({"cupom": code.strip().upper()}, NO_ID)
    if not c:
        raise HTTPException(404, "Cupão não encontrado")
    claim = await db.coupon_claims.find_one({"campaign_id": c["id"], "session_token": session_token}, NO_ID)
    if not claim:
        raise HTTPException(403, "Sessão inválida")
    record = await db.p5_charges.find_one({"claim_id": claim["id"], "status": {"$in": ["pending", "checkout", "paid"]}}, NO_ID, sort=[("created_at", -1)])
    if not record:
        return {"status": "none"}
    if record["status"] != "paid" and record["expires_at"] < now_iso():
        return {"status": "expired"}
    return {key: record[key] for key in ("id", "status", "currency", "gross_minor", "discount_minor", "net_minor")}
