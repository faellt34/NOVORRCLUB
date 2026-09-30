import os
import re
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, get_current_user, require_role, audit, notify, admin_ids, new_id, now_iso, hash_password, rate_limit

router = APIRouter(prefix="/leads")


class LeadIn(BaseModel):
    nome: str
    categoria: str
    cidade: str
    contacto: str
    nota: Optional[str] = ""


@router.post("")
async def create_lead(body: LeadIn, user: dict = Depends(get_current_user)):
    if not body.nome.strip() or not body.contacto.strip():
        raise HTTPException(status_code=400, detail="Preencha o nome do espaço e o contacto.")
    if max(len(body.nome), len(body.categoria), len(body.cidade), len(body.contacto), len(body.nota or "")) > 500:
        raise HTTPException(status_code=400, detail="Campos demasiado longos")
    await rate_limit(f"lead:{user['id']}", 10, 3600, "Limite de indicações por hora atingido.")
    lead = {"id": new_id("lead"), **body.model_dump(), "status": "Novo", "date": now_iso(),
            "referrer_id": user["id"], "referrer": user["nome"], "decision_note": None, "decided_at": None, "partner_id": None}
    await db.leads.insert_one(dict(lead))
    await audit("INDICAÇÃO", f"{body.nome} · {body.categoria} · {body.cidade} · por {user['nome']}", user, lead["id"])
    from realtime import emit
    emit("indicacao_criada", nome=body.nome, categoria=body.categoria, cidade=body.cidade, por=user["nome"], ref=lead["id"])
    await notify(await admin_ids(), "lead", "Nova indicação de parceiro", f"{user['nome']} indicou {body.nome} ({body.categoria}, {body.cidade})", "/admin")
    return lead


@router.get("")
async def list_leads(user: dict = Depends(get_current_user)):
    q = {} if user["role"] == "admin" else {"referrer_id": user["id"]}
    return await db.leads.find(q, NO_ID).sort("date", -1).to_list(500)


class DecisionIn(BaseModel):
    note: Optional[str] = ""
    email: Optional[str] = None


@router.post("/{lead_id}/approve")
async def approve_lead(lead_id: str, body: DecisionIn, user: dict = Depends(require_role("admin"))):
    lead = await db.leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        raise HTTPException(status_code=404, detail="Indicação não encontrada")
    claim = await db.leads.update_one({"id": lead_id, "status": "Novo"}, {"$set": {"status": "A aprovar"}})
    if not claim.matched_count:
        raise HTTPException(status_code=409, detail=f"Indicação já {lead['status'].lower()}")
    partner = {"id": new_id("p"), "user_id": None, "nome": lead["nome"], "categoria": lead["categoria"], "cidade": lead["cidade"],
               "status": "Ativo", "avatar": f"https://i.pravatar.cc/80?u={lead['id']}", "origem": "Indicação", "lead_id": lead_id}
    email = (body.email or (lead["contacto"] if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", lead["contacto"]) else None) or "").strip().lower()
    created_user, temp_password = None, None
    if email and not await db.users.find_one({"email": email}):
        temp_password = secrets.token_urlsafe(9)
        created_user = {"id": new_id("usr"), "email": email, "password_hash": hash_password(temp_password), "nome": lead["nome"], "role": "partner",
                        "status": "Ativo", "avatar": partner["avatar"], "handle": f"{lead['categoria']} · {lead['cidade']}", "partner_id": partner["id"], "created_at": now_iso(), "must_change_password": True}
        await db.users.insert_one(dict(created_user))
        partner["user_id"] = created_user["id"]
    await db.partners.insert_one(dict(partner))
    await db.leads.update_one({"id": lead_id}, {"$set": {"status": "Aprovada", "decision_note": body.note, "decided_at": now_iso(), "decided_by": user["nome"], "partner_id": partner["id"]}})
    await audit("APROVAÇÃO", f"Indicação {lead['nome']} aprovada → parceiro {partner['id']} criado" + (f" · acesso {email}" if created_user else ""), user, lead_id)
    await notify([lead["referrer_id"]], "lead_aprovada", "Indicação aprovada 🎉", f"{lead['nome']} foi aprovado e já é parceiro RRclub. O seu bónus será processado no próximo extrato.", "/influencer")
    emailed = False
    if created_user:
        from mailer import send_email
        emailed = await send_email(email, "RRclub · Acesso de parceiro", "Bem-vindo ao RRclub", f"A sua conta de parceiro foi criada. Palavra-passe temporária: {temp_password}\nAltere-a após o primeiro acesso.", "Entrar", f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/login")
    return {"lead": await db.leads.find_one({"id": lead_id}, NO_ID), "partner": partner, "access_email": email if created_user else None,
            "temp_password": None if emailed else temp_password, "password_emailed": emailed}


@router.post("/{lead_id}/reject")
async def reject_lead(lead_id: str, body: DecisionIn, user: dict = Depends(require_role("admin"))):
    lead = await db.leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        raise HTTPException(status_code=404, detail="Indicação não encontrada")
    if lead["status"] != "Novo":
        raise HTTPException(status_code=409, detail=f"Indicação já {lead['status'].lower()}")
    await db.leads.update_one({"id": lead_id}, {"$set": {"status": "Rejeitada", "decision_note": body.note, "decided_at": now_iso(), "decided_by": user["nome"]}})
    await audit("REJEIÇÃO", f"Indicação {lead['nome']} rejeitada" + (f" · {body.note}" if body.note else ""), user, lead_id)
    await notify([lead["referrer_id"]], "lead_rejeitada", "Indicação não aprovada", f"{lead['nome']} não foi aprovado desta vez." + (f" Motivo: {body.note}" if body.note else ""), "/influencer")
    return await db.leads.find_one({"id": lead_id}, NO_ID)
