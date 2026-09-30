import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, require_role, audit, notify, admin_ids, new_id, now_iso, hash_password, public_user

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])

COLLECTIONS = {"usuarios": "users", "influencers": "influencers", "parceiros": "partners", "campanhas": "campaigns", "ebooks": "ebooks"}
ROLE_MAP = {"Influencer": "influencer", "Parceiro": "partner", "Admin": "admin"}
ROLE_LABEL = {v: k for k, v in ROLE_MAP.items()}


def coll(kind: str):
    if kind not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Tipo desconhecido")
    return db[COLLECTIONS[kind]]


def out_user(u: dict) -> dict:
    u = public_user(u)
    u["papel"] = ROLE_LABEL.get(u.get("role"), u.get("role"))
    return u


async def resolve_campaign(data: dict) -> dict:
    if data.get("parceiro"):
        p = await db.partners.find_one({"nome": {"$regex": f"^{re.escape(data['parceiro'].strip())}$", "$options": "i"}}, NO_ID)
        if not p:
            raise HTTPException(status_code=400, detail=f"Parceiro '{data['parceiro']}' não existe. Crie-o primeiro em Parceiros.")
        data["parceiro_id"] = p["id"]
    if data.get("influencer"):
        i = await db.influencers.find_one({"$or": [{"nome": {"$regex": f"^{re.escape(data['influencer'].strip())}$", "$options": "i"}}, {"handle": data["influencer"].strip()}]}, NO_ID)
        if not i:
            raise HTTPException(status_code=400, detail=f"Influencer '{data['influencer']}' não existe.")
        data["influencer_id"] = i["id"]
    for k in ("desconto", "comissao"):
        if k in data:
            try:
                data[k] = float(str(data[k]).replace(",", "."))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Valor inválido em {k}")
    if "cupom" in data:
        data["cupom"] = data["cupom"].strip().upper()
    return data


async def prepare(kind: str, data: dict, creating: bool) -> dict:
    data = {k: v for k, v in data.items() if k not in ("id", "_id", "password_hash")}
    if kind == "campanhas":
        data = await resolve_campaign(data)
    if kind == "ebooks":
        data["premium"] = str(data.get("premium", "")).lower() in ("true", "sim", "1", "premium")
        for k in ("paginas",):
            data[k] = int(float(data.get(k) or 0))
        data["preco"] = float(str(data.get("preco") or 0).replace(",", "."))
    if kind == "usuarios":
        if "papel" in data:
            data["role"] = ROLE_MAP.get(data.pop("papel"), "influencer")
        if "email" in data:
            data["email"] = data["email"].strip().lower()
        pwd = data.pop("password", None)
        if creating:
            data["password_hash"] = hash_password(pwd or "robson123")
            data["avatar"] = data.get("avatar") or f"https://i.pravatar.cc/80?u={data.get('email')}"
            data["created_at"] = now_iso()
        elif pwd:
            data["password_hash"] = hash_password(pwd)
    return data


@router.get("/{kind}")
async def list_items(kind: str):
    items = await coll(kind).find({}, NO_ID).to_list(2000)
    if kind == "usuarios":
        items = [out_user(i) for i in items]
    if kind == "campanhas":
        parts = {p["id"]: p["nome"] async for p in db.partners.find({}, NO_ID)}
        infs = {i["id"]: i["nome"] async for i in db.influencers.find({}, NO_ID)}
        for c in items:
            c["parceiro"] = parts.get(c.get("parceiro_id"), c.get("parceiro", "—"))
            c["influencer"] = infs.get(c.get("influencer_id"), c.get("influencer", "—"))
    return items


@router.post("/{kind}")
async def create_item(kind: str, data: dict, user: dict = Depends(require_role("admin"))):
    c = coll(kind)
    data = await prepare(kind, data, True)
    if kind == "usuarios" and await db.users.find_one({"email": data.get("email")}):
        raise HTTPException(status_code=409, detail="Já existe um utilizador com este email")
    if kind == "campanhas" and await db.campaigns.find_one({"cupom": data.get("cupom")}):
        raise HTTPException(status_code=409, detail="Já existe uma campanha com este código de cupom")
    prefix = {"usuarios": "usr", "influencers": "if", "parceiros": "p", "campanhas": "c", "ebooks": "e"}[kind]
    doc = {"id": new_id(prefix), **data}
    doc.setdefault("status", "Ativo")
    await c.insert_one(dict(doc))
    label = doc.get("nome") or doc.get("titulo") or doc["id"]
    await audit("CRIAÇÃO", f"{kind} · {label}" + (f" · comissão {doc['comissao']:g}%" if kind == "campanhas" else ""), user, doc["id"])
    if kind == "campanhas":
        from realtime import emit
        emit("cupons_gerados", quantidade=1, cupom=doc.get("cupom"), campanha=label, parceiro=doc.get("parceiro"), por=user["nome"], ref=doc["id"])
        emit("cupom_gerado", cupom=doc.get("cupom"), campanha=label, ref=doc["id"])
    return out_user(doc) if kind == "usuarios" else doc


@router.put("/{kind}/{item_id}")
async def update_item(kind: str, item_id: str, data: dict, user: dict = Depends(require_role("admin"))):
    c = coll(kind)
    existing = await c.find_one({"id": item_id}, NO_ID)
    if not existing:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    data = await prepare(kind, data, False)
    await c.update_one({"id": item_id}, {"$set": data})
    doc = await c.find_one({"id": item_id}, NO_ID)
    if kind in ("parceiros", "influencers") and "status" in data and doc.get("user_id"):
        await db.users.update_one({"id": doc["user_id"]}, {"$set": {"status": data["status"]}})
        if data["status"] == "Ativo" and existing.get("status") == "Pendente":
            await notify([doc["user_id"]], "lead_aprovada", "Conta ativada 🎉", f"A sua conta {doc['nome']} foi aprovada. Já pode entrar na plataforma RRclub.", "/login")
    await audit("EDIÇÃO", f"{kind} · {doc.get('nome') or doc.get('titulo') or item_id}", user, item_id)
    return out_user(doc) if kind == "usuarios" else doc


@router.delete("/{kind}/{item_id}")
async def delete_item(kind: str, item_id: str, user: dict = Depends(require_role("admin"))):
    c = coll(kind)
    existing = await c.find_one({"id": item_id}, NO_ID)
    if not existing:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    if kind == "usuarios" and item_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não pode remover a sua própria conta")
    await c.delete_one({"id": item_id})
    await audit("REMOÇÃO", f"{kind} · {existing.get('nome') or existing.get('titulo') or item_id}", user, item_id)
    return {"ok": True}
