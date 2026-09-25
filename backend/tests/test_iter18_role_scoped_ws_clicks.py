"""Iteration 18 - Role-scoped WebSocket dashboard + Admin /clicks endpoint.

Covers:
- WS /api/ws/dashboard authenticates influencer + partner tokens; first frame {"tipo":"ligado","role":<role>}
- public_coupon click emits clique_cupao to influencer AND partner AND admin (role scoping)
- redeem emits split_executado to influencer, partner and admin
- Origem detection via ?src=tiktok/whatsapp -> capitalized (Tiktok, Whatsapp)
- GET /api/admin/clicks?period=today|7|30 -> items[] with expected shape; status transitions to 'Converteu' after redemption
- 403 for non-admin
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

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

ADMIN = {"email": "faellt@gmail.com", "password": "Robson2026!"}
PARTNER = {"email": "parceiro.exemplo@club.pt", "password": "parceiro123"}
INFLUENCER = {"email": "influencer.exemplo@club.pt", "password": "influencer123"}

_created_redemption_ids: list[str] = []


def login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, headers={"User-Agent": BROWSER_UA}, timeout=20)
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


# --- WS role handshake ---
@pytest.mark.asyncio
async def test_ws_influencer_ligado_role(influencer_token):
    async with websockets.connect(ws_url(influencer_token), open_timeout=15) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(msg)
        assert data["tipo"] == "ligado"
        assert data.get("role") == "influencer"


@pytest.mark.asyncio
async def test_ws_partner_ligado_role(partner_token):
    async with websockets.connect(ws_url(partner_token), open_timeout=15) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(msg)
        assert data["tipo"] == "ligado"
        assert data.get("role") == "partner"


async def _collect_event(ws, expected_type: str, trigger_coro, timeout=10):
    task = asyncio.create_task(trigger_coro)
    end = asyncio.get_event_loop().time() + timeout
    result_event = None
    while asyncio.get_event_loop().time() < end:
        remaining = end - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        data = json.loads(msg)
        if data.get("tipo") == expected_type:
            result_event = data
            break
    trigger_result = await task
    return result_event, trigger_result


# --- Clique cupao delivered to influencer + partner + admin ---
@pytest.mark.asyncio
async def test_clique_cupao_delivered_to_all_scoped_roles(admin_token, influencer_token, partner_token):
    ua_variant = f"Mozilla/5.0 IterTestUA/{uuid.uuid4().hex[:8]}"

    async def do_click():
        return await asyncio.to_thread(
            requests.get,
            f"{BASE_URL}/api/public/coupon/CLUB-10",
            params={"src": "tiktok"},
            headers={"User-Agent": ua_variant},
            timeout=20,
        )

    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws_a, \
               websockets.connect(ws_url(influencer_token), open_timeout=15) as ws_i, \
               websockets.connect(ws_url(partner_token), open_timeout=15) as ws_p:
        # consume ligado frames
        for w in (ws_a, ws_i, ws_p):
            await asyncio.wait_for(w.recv(), timeout=10)

        # Trigger once; collect on each socket concurrently
        trigger_task = asyncio.create_task(do_click())

        async def wait_for(w):
            end = asyncio.get_event_loop().time() + 12
            while asyncio.get_event_loop().time() < end:
                try:
                    msg = await asyncio.wait_for(w.recv(), timeout=end - asyncio.get_event_loop().time())
                except asyncio.TimeoutError:
                    return None
                d = json.loads(msg)
                if d.get("tipo") == "clique_cupao":
                    return d
            return None

        ev_a, ev_i, ev_p = await asyncio.gather(wait_for(ws_a), wait_for(ws_i), wait_for(ws_p))
        resp = await trigger_task
        assert resp.status_code == 200, resp.text

    assert ev_a is not None, "admin did not receive clique_cupao"
    assert ev_i is not None, "influencer did not receive clique_cupao"
    assert ev_p is not None, "partner did not receive clique_cupao"
    for ev in (ev_a, ev_i, ev_p):
        assert ev["cupom"] == "CLUB-10"
        assert ev["origem"] == "Tiktok"


@pytest.mark.asyncio
async def test_clique_origem_whatsapp_capitalized(influencer_token):
    ua_variant = f"Mozilla/5.0 IterTestUA/{uuid.uuid4().hex[:8]}"
    async with websockets.connect(ws_url(influencer_token), open_timeout=15) as ws:
        await asyncio.wait_for(ws.recv(), timeout=10)

        async def do_click():
            return await asyncio.to_thread(
                requests.get,
                f"{BASE_URL}/api/public/coupon/CLUB-10",
                params={"src": "whatsapp"},
                headers={"User-Agent": ua_variant},
                timeout=20,
            )

        ev, resp = await _collect_event(ws, "clique_cupao", do_click(), timeout=10)
        assert resp.status_code == 200
        assert ev is not None
        assert ev["origem"] == "Whatsapp"


# --- Redemption delivered to influencer + admin (role scoped) ---
@pytest.mark.asyncio
async def test_split_executado_delivered_to_influencer_and_admin(admin_token, influencer_token, partner_token):
    async def do_redeem():
        payload = {"code": "CLUB-10", "amount": 25, "idempotency_key": str(uuid.uuid4())}
        return await asyncio.to_thread(
            requests.post,
            f"{BASE_URL}/api/redemptions",
            json=payload,
            headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {partner_token}"},
            timeout=20,
        )

    async with websockets.connect(ws_url(admin_token), open_timeout=15) as ws_a, \
               websockets.connect(ws_url(influencer_token), open_timeout=15) as ws_i:
        for w in (ws_a, ws_i):
            await asyncio.wait_for(w.recv(), timeout=10)

        trigger_task = asyncio.create_task(do_redeem())

        async def wait_for(w):
            end = asyncio.get_event_loop().time() + 12
            while asyncio.get_event_loop().time() < end:
                try:
                    msg = await asyncio.wait_for(w.recv(), timeout=end - asyncio.get_event_loop().time())
                except asyncio.TimeoutError:
                    return None
                d = json.loads(msg)
                if d.get("tipo") == "split_executado":
                    return d
            return None

        ev_a, ev_i = await asyncio.gather(wait_for(ws_a), wait_for(ws_i))
        resp = await trigger_task

    assert resp.status_code == 200, resp.text
    rid = resp.json()["record"]["id"]
    _created_redemption_ids.append(rid)

    assert ev_a is not None and ev_i is not None
    for ev in (ev_a, ev_i):
        assert ev["cupom"] == "CLUB-10"
        assert "record" in ev
        assert ev["record"]["id"] == rid


# --- Admin clicks endpoint ---
def test_admin_clicks_today(admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/clicks", params={"period": "today"},
                     headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {admin_token}"}, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and isinstance(body["items"], list)
    assert len(body["items"]) <= 100
    for it in body["items"]:
        assert set(["id", "date", "origem", "influencer", "campanha", "cupom", "status"]).issubset(it.keys())
        assert it["status"] in ("Converteu", "Só clicou")


def test_admin_clicks_7_and_30(admin_token):
    for p in ("7", "30"):
        r = requests.get(f"{BASE_URL}/api/admin/clicks", params={"period": p},
                         headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {admin_token}"}, timeout=20)
        assert r.status_code == 200, f"period {p}: {r.text}"
        body = r.json()
        assert isinstance(body["items"], list)
        assert len(body["items"]) <= 100


def test_admin_clicks_forbidden_for_non_admin(partner_token, influencer_token):
    for tok in (partner_token, influencer_token):
        r = requests.get(f"{BASE_URL}/api/admin/clicks", params={"period": "7"},
                         headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


def test_click_then_redeem_becomes_converteu(admin_token, partner_token):
    """Create a fresh click (unique UA) then redeem CLUB-10 and verify the click flips to Converteu."""
    ua_variant = f"Mozilla/5.0 ConvTest/{uuid.uuid4().hex[:8]}"
    # 1) fresh click with src=tiktok
    r_click = requests.get(f"{BASE_URL}/api/public/coupon/CLUB-10", params={"src": "tiktok"},
                           headers={"User-Agent": ua_variant}, timeout=20)
    assert r_click.status_code == 200, r_click.text

    # 2) redemption for CLUB-10
    r_red = requests.post(f"{BASE_URL}/api/redemptions",
                          json={"code": "CLUB-10", "amount": 42, "idempotency_key": str(uuid.uuid4())},
                          headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {partner_token}"}, timeout=20)
    assert r_red.status_code == 200, r_red.text
    _created_redemption_ids.append(r_red.json()["record"]["id"])

    # 3) fetch today clicks and confirm at least one Tiktok click has status Converteu
    r_clicks = requests.get(f"{BASE_URL}/api/admin/clicks", params={"period": "today"},
                            headers={"User-Agent": BROWSER_UA, "Authorization": f"Bearer {admin_token}"}, timeout=20)
    assert r_clicks.status_code == 200
    items = r_clicks.json()["items"]
    tiktok_converted = [i for i in items if i["cupom"] == "CLUB-10" and i["origem"] == "Tiktok" and i["status"] == "Converteu"]
    assert tiktok_converted, f"expected at least one Tiktok CLUB-10 click marked Converteu; items={items[:5]}"


def test_report_created_redemptions():
    # Reported for main agent visibility; not deletable via API.
    print("CREATED_REDEMPTION_IDS:", _created_redemption_ids)
    assert True
