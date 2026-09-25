"""Iteration 17 - Admin realtime WebSocket dashboard tests.

Covers:
- /api/ws/dashboard connect with admin JWT -> {"tipo":"ligado"}
- Connect with non-admin/no token -> closed with code 4401
- ping -> pong
- redemption -> split_executado event
- lead creation -> indicacao_criada event
- campaign creation -> cupons_gerados event
"""
import asyncio
import json
import os
import uuid

import pytest
import requests
import websockets
import websockets.exceptions as ws_exc

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
WS_BASE = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")
UA = {"User-Agent": "Mozilla/5.0 (backend-test)"}

ADMIN = {"email": "faellt@gmail.com", "password": "Robson2026!"}
PARTNER = {"email": "parceiro.exemplo@club.pt", "password": "parceiro123"}
INFLUENCER = {"email": "influencer.exemplo@club.pt", "password": "influencer123"}


def login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, headers=UA, timeout=20)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return login(ADMIN)


@pytest.fixture(scope="module")
def partner_token():
    return login(PARTNER)


@pytest.fixture(scope="module")
def influencer_token():
    return login(INFLUENCER)


def ws_url(token: str) -> str:
    return f"{WS_BASE}/api/ws/dashboard?token={token}"


# --- Connect / Auth ---
@pytest.mark.asyncio
async def test_ws_admin_connect_ligado(admin_token):
    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(msg)
        assert data["tipo"] == "ligado"
        assert "clientes" in data


@pytest.mark.asyncio
async def test_ws_ping_pong(admin_token):
    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws:
        # consume "ligado"
        await asyncio.wait_for(ws.recv(), timeout=10)
        await ws.send("ping")
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        assert json.loads(msg)["tipo"] == "pong"


_REJECT_EXC = tuple(
    getattr(ws_exc, n) for n in ("InvalidStatus", "InvalidStatusCode", "ConnectionClosed")
    if hasattr(ws_exc, n)
)


@pytest.mark.asyncio
async def test_ws_influencer_rejected(influencer_token):
    with pytest.raises(_REJECT_EXC):
        async with websockets.connect(ws_url(influencer_token), open_timeout=15) as ws:
            await asyncio.wait_for(ws.recv(), timeout=5)


@pytest.mark.asyncio
async def test_ws_no_token_rejected():
    with pytest.raises(_REJECT_EXC):
        async with websockets.connect(f"{WS_BASE}/api/ws/dashboard?token=", open_timeout=15) as ws:
            await asyncio.wait_for(ws.recv(), timeout=5)


async def _collect_event(ws, expected_type: str, trigger_coro, timeout=8):
    """Run trigger and wait for event of given type."""
    task = asyncio.create_task(trigger_coro)
    end = asyncio.get_event_loop().time() + timeout
    result_event = None
    trigger_result = None
    while asyncio.get_event_loop().time() < end:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=end - asyncio.get_event_loop().time())
        except asyncio.TimeoutError:
            break
        data = json.loads(msg)
        if data.get("tipo") == expected_type:
            result_event = data
            break
    trigger_result = await task
    return result_event, trigger_result


# --- Business event emissions ---
@pytest.mark.asyncio
async def test_ws_split_executado_on_redemption(admin_token, partner_token):
    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws:
        await asyncio.wait_for(ws.recv(), timeout=10)  # "ligado"

        async def do_redeem():
            payload = {"code": "CLUB-10", "amount": 30, "idempotency_key": str(uuid.uuid4())}
            return await asyncio.to_thread(
                requests.post,
                f"{BASE_URL}/api/redemptions",
                json=payload,
                headers={**UA, "Authorization": f"Bearer {partner_token}"},
                timeout=20,
            )

        event, resp = await _collect_event(ws, "split_executado", do_redeem(), timeout=10)
        assert resp.status_code == 200, resp.text
        assert event is not None, "split_executado not received"
        assert event["cupom"] == "CLUB-10"
        assert event["origem"] == "loja"
        assert float(event["valor_plataforma"]) == pytest.approx(3.0, abs=0.01)


@pytest.mark.asyncio
async def test_ws_indicacao_criada(admin_token, influencer_token):
    lead_id_holder = {}
    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws:
        await asyncio.wait_for(ws.recv(), timeout=10)

        async def do_lead():
            payload = {"nome": "WS Test Lead", "categoria": "Restaurante", "cidade": "Lisboa",
                       "contacto": "ws@test.pt", "nota": ""}
            r = await asyncio.to_thread(
                requests.post,
                f"{BASE_URL}/api/leads",
                json=payload,
                headers={**UA, "Authorization": f"Bearer {influencer_token}"},
                timeout=20,
            )
            if r.status_code == 200:
                lead_id_holder["id"] = r.json()["id"]
            return r

        event, resp = await _collect_event(ws, "indicacao_criada", do_lead(), timeout=10)
        assert resp.status_code == 200, resp.text
        assert event is not None, "indicacao_criada not received"
        assert event["nome"] == "WS Test Lead"

    # Cleanup: reject lead
    if lead_id_holder.get("id"):
        r = requests.post(
            f"{BASE_URL}/api/leads/{lead_id_holder['id']}/reject",
            json={"note": "teste"},
            headers={**UA, "Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_ws_cupons_gerados(admin_token):
    camp_id_holder = {}
    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws:
        await asyncio.wait_for(ws.recv(), timeout=10)

        async def do_camp():
            payload = {"nome": "WS Camp", "parceiro": "Parceiro Exemplo", "influencer": "@exemplo",
                       "cupom": "WSTEST-5", "desconto": 5, "comissao": 10,
                       "validade": "2027-12-31", "status": "Ativa"}
            r = await asyncio.to_thread(
                requests.post,
                f"{BASE_URL}/api/admin/campanhas",
                json=payload,
                headers={**UA, "Authorization": f"Bearer {admin_token}"},
                timeout=20,
            )
            if r.status_code == 200:
                camp_id_holder["id"] = r.json()["id"]
            return r

        event, resp = await _collect_event(ws, "cupons_gerados", do_camp(), timeout=10)
        assert resp.status_code == 200, resp.text
        assert event is not None, "cupons_gerados not received"
        assert event["cupom"] == "WSTEST-5"
        assert int(event["quantidade"]) == 1

    # Cleanup
    if camp_id_holder.get("id"):
        r = requests.delete(
            f"{BASE_URL}/api/admin/campanhas/{camp_id_holder['id']}",
            headers={**UA, "Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
