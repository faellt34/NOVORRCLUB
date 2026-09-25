import asyncio
import json
import logging
import os

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core import db, JWT_ALGORITHM, now_iso

logger = logging.getLogger(__name__)
router = APIRouter()
_clients: set[WebSocket] = set()


async def broadcast(tipo: str, **data):
    msg = json.dumps({"tipo": tipo, "ts": now_iso(), **data}, ensure_ascii=False)
    dead = []
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


def emit(tipo: str, **data):
    try:
        asyncio.get_running_loop().create_task(broadcast(tipo, **data))
    except RuntimeError:
        pass


async def _admin_from_token(token: str):
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "id": 1, "role": 1, "status": 1})
    return user if user and user.get("role") == "admin" and user.get("status") == "Ativo" else None


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket, token: str = ""):
    if not await _admin_from_token(token):
        await ws.close(code=4401)
        return
    await ws.accept()
    _clients.add(ws)
    await ws.send_text(json.dumps({"tipo": "ligado", "ts": now_iso(), "clientes": len(_clients)}))
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
        _clients.discard(ws)
