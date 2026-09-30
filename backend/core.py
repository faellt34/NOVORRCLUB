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


TOKEN_TTL = timedelta(hours=24)
ROLES = ("admin", "influencer", "partner")


def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "email": email, "role": role, "type": "access", "jti": uuid.uuid4().hex, "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def public_user(user: dict) -> dict:
    u = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    return u


def request_token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token or None


async def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub", "jti"]})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    if payload.get("type") != "access" or not isinstance(payload.get("sub"), str) or payload.get("role") not in ROLES:
        raise HTTPException(status_code=401, detail="Token inválido")
    if await db.revoked_tokens.find_one({"jti": payload["jti"]}, {"_id": 1}):
        raise HTTPException(status_code=401, detail="Sessão terminada")
    return payload


async def revoke_token(token: Optional[str]):
    if not token:
        return
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
    except jwt.InvalidTokenError:
        return
    if payload.get("jti"):
        await db.revoked_tokens.update_one({"jti": payload["jti"]}, {"$set": {"jti": payload["jti"], "exp": payload.get("exp"), "sub": payload.get("sub"), "date": now_iso()}}, upsert=True)


async def user_from_token(token: str) -> dict:
    payload = await decode_token(token)
    user = await db.users.find_one({"id": payload["sub"]})
    if not user or user.get("role") != payload["role"]:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado")
    if user.get("status") == "Suspenso":
        raise HTTPException(status_code=403, detail="Conta suspensa")
    if user.get("tokens_invalid_before") and payload.get("iat") and payload["iat"] < user["tokens_invalid_before"]:
        raise HTTPException(status_code=401, detail="Sessão terminada")
    return public_user(user)


async def get_current_user(request: Request) -> dict:
    token = request_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return await user_from_token(token)


async def rate_limit(key: str, limit: int, window_s: int, detail: str = "Demasiados pedidos. Tente novamente mais tarde."):
    now = datetime.now(timezone.utc)
    doc = await db.rate_limits.find_one({"key": key})
    if doc and datetime.fromisoformat(doc["start"]) + timedelta(seconds=window_s) > now:
        if doc["count"] >= limit:
            raise HTTPException(status_code=429, detail=detail)
        await db.rate_limits.update_one({"key": key}, {"$inc": {"count": 1}})
    else:
        await db.rate_limits.update_one({"key": key}, {"$set": {"key": key, "start": now.isoformat(), "count": 1}}, upsert=True)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?"))


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
            await email_user(uid, f"RRclub · {titulo}", titulo, texto, "Abrir no RRclub", link)


EMAIL_TYPES = {"lead_aprovada", "lead_rejeitada", "pagamento", "compra", "lead", "reset"}


async def admin_ids():
    return [u["id"] async for u in db.users.find({"role": "admin"}, {"id": 1})]
