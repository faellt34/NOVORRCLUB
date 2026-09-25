import asyncio
import json
import logging
import os

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core import db, JWT_ALGORITHM, now_iso

logger = logging.getLogger(__name__)
router = APIRouter()
_clients: dict[WebSocket, dict] = {}


def _visible(user: dict, ev: dict) -> bool:
    role = user.get("role")
    if role == "admin":
        return True
    if role == "influencer":
        return ev.get("influencer_id") == user.get("influencer_id")
    if role == "partner":
        return ev.get("partner_id") == user.get("partner_id")
    return False


async def broadcast(tipo: str, **data):
    ev = {"tipo": tipo, "ts": now_iso(), **data}
    msg = json.dumps(ev, ensure_ascii=False)
    for ws, user in list(_clients.items()):
        if not _visible(user, ev):
            continue
        try:
            await ws.send_text(msg)
        except Exception:
            _clients.pop(ws, None)


def emit(tipo: str, **data):
    try:
        asyncio.get_running_loop().create_task(broadcast(tipo, **data))
    except RuntimeError:
        pass


async def _user_from_token(token: str):
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "id": 1, "role": 1, "status": 1, "influencer_id": 1, "partner_id": 1})
    return user if user and user.get("status") == "Ativo" else None


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket, token: str = ""):
    user = await _user_from_token(token)
    if not user:
        await ws.close(code=4401)
        return
    await ws.accept()
    _clients[ws] = user
    await ws.send_text(json.dumps({"tipo": "ligado", "ts": now_iso(), "role": user["role"]}))
    try:
        while True:
            try:
                txt = await asyncio.wait_for(ws.receive_text(), timeout=25)
                if txt == "ping":
                    await ws.send_text('{"tipo":"pong"}')
            except asyncio.TimeoutError:
                await ws.send_text('{"tipo":"pong"}')
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _clients.pop(ws, None)
