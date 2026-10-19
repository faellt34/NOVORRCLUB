"""Google ID token validation. No provider calls are made at import time."""
import asyncio
import os
from fastapi import HTTPException


async def verify_google_credential(credential: str, nonce: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(503, "O acesso Google ainda não está configurado.")
    try:
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request
        claims = await asyncio.to_thread(id_token.verify_oauth2_token, credential, Request(), client_id)
    except Exception:
        raise HTTPException(401, "Não foi possível validar a conta Google. Tente novamente.")
    if (claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com")
            or claims.get("email_verified") is not True or not claims.get("email")
            or not claims.get("sub") or claims.get("nonce") != nonce):
        raise HTTPException(401, "Identidade Google inválida ou pedido expirado.")
    return claims

