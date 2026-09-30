import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from core import db, decode_token, now_iso

logger = logging.getLogger(__name__)
router = APIRouter()
_clients: dict[WebSocket, dict] = {}
_lock = asyncio.Lock()
MAX_PER_USER = 5
AUTH_TIMEOUT = 8


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
    async with _lock:
        targets = [ws for ws, user in _clients.items() if _visible(user, ev)]
    for ws in targets:
        try:
            await ws.send_text(msg)
        except Exception:
            async with _lock:
                _clients.pop(ws, None)


def emit(tipo: str, **data):
    try:
        asyncio.get_running_loop().create_task(broadcast(tipo, **data))
    except RuntimeError:
        pass


async def _user_from_token(token: str):
    try:
        payload = await decode_token(token)
    except HTTPException:
        return None
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "id": 1, "role": 1, "status": 1, "influencer_id": 1, "partner_id": 1})
    return user if user and user.get("status") == "Ativo" and user.get("role") == payload["role"] else None


async def _authenticate(ws: WebSocket):
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=AUTH_TIMEOUT)
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("type") != "auth" or not isinstance(data.get("token"), str):
        return None
    return await _user_from_token(data["token"])


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    user = await _authenticate(ws)
    if not user:
        await ws.close(code=4401)
        return
    async with _lock:
        if sum(1 for u in _clients.values() if u["id"] == user["id"]) >= MAX_PER_USER:
            await ws.close(code=4429)
            return
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
        async with _lock:
            _clients.pop(ws, None)
