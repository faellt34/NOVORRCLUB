from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, get_current_user, notify, new_id, now_iso, rate_limit

router = APIRouter(prefix="/messages")
MAX_TEXT = 2000


async def allowed_contacts(user: dict):
    if user["role"] == "admin":
        return await db.users.find({"id": {"$ne": user["id"]}}, {**NO_ID, "password_hash": 0}).to_list(500)
    admins = await db.users.find({"role": "admin"}, {**NO_ID, "password_hash": 0}).to_list(50)
    if user["role"] == "influencer":
        camps = await db.campaigns.find({"influencer_id": user.get("influencer_id")}, NO_ID).to_list(500)
        others = await db.users.find({"partner_id": {"$in": [c["parceiro_id"] for c in camps]}}, {**NO_ID, "password_hash": 0}).to_list(500)
    else:
        camps = await db.campaigns.find({"parceiro_id": user.get("partner_id")}, NO_ID).to_list(500)
        others = await db.users.find({"influencer_id": {"$in": [c["influencer_id"] for c in camps]}}, {**NO_ID, "password_hash": 0}).to_list(500)
    return admins + others


@router.get("/contacts")
async def contacts(user: dict = Depends(get_current_user)):
    return await allowed_contacts(user)


async def conv_view(conv: dict, me: str):
    other_id = next((p for p in conv["participants"] if p != me), me)
    other = await db.users.find_one({"id": other_id}, {**NO_ID, "password_hash": 0}) or {"id": other_id, "nome": "Utilizador removido", "role": "—", "avatar": ""}
    unread = await db.messages.count_documents({"conversation_id": conv["id"], "sender_id": {"$ne": me}, "read_by": {"$ne": me}})
    return {**conv, "other": other, "unread": unread}


@router.get("/conversations")
async def conversations(user: dict = Depends(get_current_user)):
    convs = await db.conversations.find({"participants": user["id"]}, NO_ID).sort("updated_at", -1).to_list(200)
    return [await conv_view(c, user["id"]) for c in convs]


class ConvIn(BaseModel):
    participant_id: str
    text: Optional[str] = None


@router.post("/conversations")
async def create_conversation(body: ConvIn, user: dict = Depends(get_current_user)):
    if body.participant_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não pode conversar consigo próprio")
    allowed = {c["id"] for c in await allowed_contacts(user)}
    if body.participant_id not in allowed:
        raise HTTPException(status_code=403, detail="Não pode iniciar conversa com este utilizador")
    conv = await db.conversations.find_one({"participants": {"$all": [user["id"], body.participant_id], "$size": 2}}, NO_ID)
    if not conv:
        conv = {"id": new_id("conv"), "participants": [user["id"], body.participant_id], "last_message": None, "updated_at": now_iso(), "created_at": now_iso()}
        await db.conversations.insert_one(dict(conv))
    if body.text:
        await send_message(conv["id"], MsgIn(text=body.text), user)
        conv = await db.conversations.find_one({"id": conv["id"]}, NO_ID)
    return await conv_view(conv, user["id"])


class MsgIn(BaseModel):
    text: str


@router.get("/conversations/{conv_id}")
async def get_messages(conv_id: str, user: dict = Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id, "participants": user["id"]}, NO_ID)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    await db.messages.update_many({"conversation_id": conv_id, "sender_id": {"$ne": user["id"]}, "read_by": {"$ne": user["id"]}}, {"$addToSet": {"read_by": user["id"]}})
    msgs = await db.messages.find({"conversation_id": conv_id}, NO_ID).sort("date", 1).to_list(500)
    return {"conversation": await conv_view(conv, user["id"]), "messages": msgs}


@router.post("/conversations/{conv_id}")
async def send_message(conv_id: str, body: MsgIn, user: dict = Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    if len(text) > MAX_TEXT:
        raise HTTPException(status_code=400, detail=f"Mensagem demasiado longa (máx. {MAX_TEXT} caracteres)")
    await rate_limit(f"msg:{user['id']}", 30, 60, "Está a enviar mensagens demasiado depressa. Aguarde um minuto.")
    conv = await db.conversations.find_one({"id": conv_id, "participants": user["id"]}, NO_ID)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    msg = {"id": new_id("m"), "conversation_id": conv_id, "sender_id": user["id"], "sender": user["nome"], "text": text, "date": now_iso(), "read_by": [user["id"]]}
    await db.messages.insert_one(dict(msg))
    await db.conversations.update_one({"id": conv_id}, {"$set": {"last_message": text[:120], "last_sender": user["nome"], "updated_at": msg["date"]}})
    others = [p for p in conv["participants"] if p != user["id"]]
    await notify(others, "mensagem", f"Mensagem de {user['nome']}", text[:140], "/mensagens")
    return msg


@router.get("/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    convs = [c["id"] async for c in db.conversations.find({"participants": user["id"]}, {"id": 1})]
    n = await db.messages.count_documents({"conversation_id": {"$in": convs}, "sender_id": {"$ne": user["id"]}, "read_by": {"$ne": user["id"]}})
    return {"unread": n}
