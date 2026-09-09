import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
NO_ID = {"_id": 0}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def public_user(user: dict) -> dict:
    u = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    return u


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token inválido")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado")
    if user.get("status") == "Suspenso":
        raise HTTPException(status_code=403, detail="Conta suspensa")
    return public_user(user)


def require_role(*roles):
    async def dep(user: dict = Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Sem permissão para esta operação")
        return user
    return dep


async def audit(action: str, detail: str, actor: Optional[dict] = None, ref: Optional[str] = None):
    entry = {"id": new_id("a"), "action": action, "detail": detail, "date": now_iso(),
             "actor_id": actor.get("id") if actor else "system",
             "actor": actor.get("nome") if actor else "Sistema", "ref": ref}
    await db.audit_log.insert_one(entry)
    entry.pop("_id", None)
    return entry


async def notify(user_ids, tipo: str, titulo: str, texto: str, link: str = None):
    ids = [i for i in set(user_ids) if i]
    if not ids:
        return
    docs = [{"id": new_id("n"), "user_id": uid, "tipo": tipo, "titulo": titulo, "texto": texto,
             "link": link, "lido": False, "date": now_iso()} for uid in ids]
    await db.notifications.insert_many(docs)
    if tipo in EMAIL_TYPES:
        from mailer import email_user
        for uid in ids:
            await email_user(uid, f"ןןClub · {titulo}", titulo, texto, "Abrir no ןןClub", link)


EMAIL_TYPES = {"lead_aprovada", "lead_rejeitada", "pagamento", "compra", "lead", "reset"}


async def admin_ids():
    return [u["id"] async for u in db.users.find({"role": "admin"}, {"id": 1})]
