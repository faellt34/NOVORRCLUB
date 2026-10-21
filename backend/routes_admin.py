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
    if data.get("parceiro_id"):
        partner = await db.partners.find_one({"id": data["parceiro_id"]}, NO_ID)
        if not partner:
            raise HTTPException(400, "Parceiro não encontrado")
        currency = partner.get("currency", "eur")
        if data.get("currency") and data["currency"] != currency:
            raise HTTPException(400, "A moeda da campanha deve corresponder à do parceiro")
        data["currency"] = currency
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
    if kind in ("parceiros", "campanhas") and "currency" in data:
        data["currency"] = str(data["currency"]).lower()
        if data["currency"] not in ("eur", "brl"):
            raise HTTPException(400, "Moeda inválida")
    if kind == "campanhas":
        data = await resolve_campaign(data)
        # Historical clients can submit "Ativo" (masculine); normalize only
        # the current write, never bulk-update stored campaigns or payments.
        if data.get("status") == "Ativo":
            data["status"] = "Ativa"
    if kind == "ebooks":
        data["premium"] = str(data.get("premium", "")).lower() in ("true", "sim", "1", "premium")
        for k in ("paginas",):
            data[k] = int(float(data.get(k) or 0))
        data["preco"] = float(str(data.get("preco") or 0).replace(",", "."))
    if (kind == "usuarios" and "partner_id" in data) or (kind == "parceiros" and "user_id" in data):
        raise HTTPException(400, "Use a ação Associar conta para alterar a ligação ao estabelecimento.")
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
    # Campaigns use the feminine "Ativa"; partner/user records use "Ativo".
    # P5 and public coupon routes require campaigns.status == "Ativa".
    doc.setdefault("status", "Ativa" if kind == "campanhas" else "Ativo")
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
    if kind in ("parceiros", "campanhas") and "currency" in data and data["currency"] != existing.get("currency", "eur"):
        history_key = "partner_id" if kind == "parceiros" else "campaign_id"
        if existing.get("stripe_account_id") or existing.get("pix_stripe_account_id") or await db.redemptions.find_one({history_key: item_id}) or await db.payment_transactions.find_one({history_key: item_id}):
            raise HTTPException(409, "Este registo já tem recebimentos configurados ou histórico financeiro. Crie um novo registo para mudar de moeda.")
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


class PartnerAccountIn(BaseModel):
    user_id: str


@router.post('/parceiros/{partner_id}/conta')
async def associate_partner_account(partner_id: str, body: PartnerAccountIn, admin: dict = Depends(require_role('admin'))):
    """Explicit repair only. Never reassign an already-owned user or business."""
    partner = await db.partners.find_one({'id': partner_id}, NO_ID)
    account = await db.users.find_one({'id': body.user_id}, NO_ID)
    if not partner or not account:
        raise HTTPException(404, 'Conta ou estabelecimento não encontrado.')
    if account.get('role') != 'partner':
        raise HTTPException(400, 'Selecione uma conta com papel Parceiro.')
    notas = []
    if partner.get('user_id') and partner['user_id'] != account['id']:
        if await db.users.find_one({'id': partner['user_id']}, {'_id': 1}):
            raise HTTPException(409, 'Este estabelecimento já pertence a outra conta. A reassociação exige revisão manual.')
        notas.append(f"estabelecimento apontava para conta inexistente {partner['user_id']}")
    prev_pid = account.get('partner_id')
    if prev_pid and prev_pid != partner_id:
        if await db.partners.find_one({'id': prev_pid}, {'_id': 1}):
            raise HTTPException(409, 'Esta conta já está ligada a outro estabelecimento.')
        notas.append(f"conta apontava para estabelecimento inexistente {prev_pid}")
    acc_cur, part_cur = account.get('currency'), partner.get('currency', 'eur')
    if acc_cur is None:
        notas.append(f"moeda da conta ausente; herdada do estabelecimento ({part_cur})")
    elif acc_cur != part_cur:
        raise HTTPException(409, 'A moeda da conta e do estabelecimento deve coincidir. Nenhuma moeda foi alterada.')
    if await db.users.find_one({'partner_id': partner_id, 'id': {'$ne': account['id']}}) or await db.partners.find_one({'user_id': account['id'], 'id': {'$ne': partner_id}}):
        raise HTTPException(409, 'Foram encontradas associações em conflito. Contacte o administrador.')
    old_owner = partner.get('user_id')
    reserved = await db.partners.update_one({'id': partner_id, 'user_id': old_owner}, {'$set': {'user_id': account['id']}})
    if not reserved.matched_count:
        raise HTTPException(409, 'O estabelecimento foi alterado durante o pedido. Atualize a página.')
    sets = {'partner_id': partner_id}
    if acc_cur is None:
        sets['currency'] = part_cur
    linked = await db.users.update_one({'id': account['id'], 'role': 'partner', 'partner_id': prev_pid, 'currency': acc_cur}, {'$set': sets})
    if not linked.matched_count:
        await db.partners.update_one({'id': partner_id, 'user_id': account['id']}, {'$set': {'user_id': old_owner}})
        raise HTTPException(409, 'A conta mudou durante o pedido. Atualize a página e verifique as associações.')
    detalhe = f"Conta {account['id']} ligada ao estabelecimento {partner_id}; sem alterações financeiras"
    if notas:
        detalhe += " · reparação: " + "; ".join(notas)
    await audit('ASSOCIAÇÃO', detalhe, admin, partner_id)
    return {'ok': True, 'partner_id': partner_id, 'user_id': account['id'], 'reparacoes': notas}
