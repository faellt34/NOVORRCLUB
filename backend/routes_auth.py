import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from core import db, verify_password, create_access_token, public_user, get_current_user, audit, now_iso, new_id, hash_password, notify, admin_ids, rate_limit, client_ip, request_token, revoke_token

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")
PASSWORD_MSG = "A palavra-passe deve ter pelo menos 8 caracteres, incluindo letras e números"
COOKIE_MAX_AGE = 24 * 3600

router = APIRouter(prefix="/auth")


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = client_ip(request)
    await rate_limit(f"login:{ip}", 30, 900, "Demasiadas tentativas a partir deste endereço. Tente novamente em 15 minutos.")
    ident = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = datetime.fromisoformat(attempt["last"]) + timedelta(minutes=15)
        if datetime.now(timezone.utc) < locked_until:
            raise HTTPException(status_code=429, detail="Demasiadas tentativas. Tente novamente em 15 minutos.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last": now_iso()}}, upsert=True)
        raise HTTPException(status_code=401, detail="Email ou palavra-passe incorretos")
    if user.get("status") == "Suspenso":
        raise HTTPException(status_code=403, detail="Conta suspensa. Contacte o administrador.")
    if user.get("status") == "Pendente":
        raise HTTPException(status_code=403, detail="A sua conta de parceiro aguarda aprovação da equipa RRclub. Será notificado quando estiver ativa.")
    await db.login_attempts.delete_one({"identifier": ident})
    token = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=COOKIE_MAX_AGE, path="/")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now_iso()}})
    await audit("LOGIN", f"{user['nome']} · {user['role']}", public_user(user))
    return {"token": token, "user": public_user(user)}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    await revoke_token(request_token(request))
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


class RegisterIn(BaseModel):
    nome: str
    email: str
    password: str
    role: str
    handle: Optional[str] = ""
    cidade: str = "Lisboa"
    categoria: Optional[str] = "Restaurante"
    telefone: Optional[str] = ""
    aceita_termos: bool = False


@router.post("/register")
async def register(body: RegisterIn, request: Request, response: Response):
    await rate_limit(f"register:{client_ip(request)}", 5, 3600, "Demasiados registos a partir deste endereço. Tente novamente mais tarde.")
    email = body.email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="Email inválido")
    if not 2 <= len(body.nome.strip()) <= 80:
        raise HTTPException(status_code=400, detail="Indique o seu nome")
    if not PASSWORD_RE.match(body.password):
        raise HTTPException(status_code=400, detail=PASSWORD_MSG)
    if body.role not in ("influencer", "partner"):
        raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    if not body.aceita_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar a Política de Privacidade")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")
    uid = new_id("usr")
    avatar = f"https://i.pravatar.cc/80?u={email}"
    user = {"id": uid, "email": email, "password_hash": hash_password(body.password), "nome": body.nome.strip(), "role": body.role, "avatar": avatar,
            "telefone": body.telefone, "created_at": now_iso(), "origem": "Registo no site"}
    if body.role == "influencer":
        handle = body.handle.strip() if body.handle else ""
        if handle and not handle.startswith("@"):
            handle = "@" + handle
        ent = {"id": new_id("if"), "user_id": uid, "nome": user["nome"], "handle": handle or email.split("@")[0], "cidade": body.cidade, "status": "Ativo", "avatar": avatar}
        await db.influencers.insert_one(dict(ent))
        user.update({"handle": ent["handle"], "influencer_id": ent["id"], "status": "Ativo"})
    else:
        ent = {"id": new_id("p"), "user_id": uid, "nome": user["nome"], "categoria": body.categoria, "cidade": body.cidade, "status": "Pendente", "avatar": avatar, "origem": "Registo no site"}
        await db.partners.insert_one(dict(ent))
        user.update({"handle": f"{body.categoria} · {body.cidade}", "partner_id": ent["id"], "status": "Pendente"})
    await db.users.insert_one(dict(user))
    pub = public_user(user)
    await audit("REGISTO", f"{user['nome']} · {body.role} · {email}" + (" · aguarda aprovação" if body.role == "partner" else ""), pub, uid)
    await notify(await admin_ids(), "registo", "Novo registo" + (" de parceiro (aprovação necessária)" if body.role == "partner" else " de influencer"),
                 f"{user['nome']} ({email}) criou conta como {'parceiro' if body.role == 'partner' else 'influencer'}" + (f" · {body.categoria}, {body.cidade}. Ative-o em Gestão › Parceiros." if body.role == "partner" else "."), "/admin/gestao")
    if body.role == "partner":
        return {"pending": True, "user": pub, "message": "Conta criada! A equipa RRclub vai verificar o seu espaço e ativar o acesso em breve. Receberá uma notificação."}
    token = create_access_token(uid, email, body.role)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=COOKIE_MAX_AGE, path="/")
    return {"pending": False, "token": token, "user": pub}
