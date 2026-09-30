"""Iteration 31 — Top 10 security fixes + Diretor apply-correction endpoint.

Covers:
- JWT structure (jti/iat/exp ~24h) and logout revocation
- Register password policy
- WebSocket auth via first message (invalid + timeout)
- Message length validation (>2000 chars → 400)
- Diretor apply-correction endpoint (403/404/409, propose→approve→apply flow)
"""
import asyncio
import json
import os
import time
import uuid

import jwt as pyjwt
import pytest
import requests
import websockets

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    except FileNotFoundError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()
WS_URL = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/dashboard"

ADMIN_EMAIL = "faellt@gmail.com"
ADMIN_PASSWORD = "Robson2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- JWT structure & revocation ---
class TestJwtLogout:
    def test_token_has_jti_iat_exp_24h(self, admin_token):
        payload = pyjwt.decode(admin_token, options={"verify_signature": False})
        assert "jti" in payload and isinstance(payload["jti"], str)
        assert "iat" in payload and "exp" in payload
        # exp - iat should be ~ 24h (86400s), allow tolerance
        assert 86000 <= payload["exp"] - payload["iat"] <= 86800

    def test_me_ok_then_logout_revokes(self):
        # New session token for this test so we can revoke it without affecting other tests
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        tok = r.json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=h)
        assert me.status_code == 200
        lo = requests.post(f"{BASE_URL}/api/auth/logout", headers=h)
        assert lo.status_code == 200
        me2 = requests.get(f"{BASE_URL}/api/auth/me", headers=h)
        assert me2.status_code == 401
        assert "Sessão terminada" in me2.text or "terminada" in me2.text.lower()


# --- Register password policy ---
class TestRegisterPassword:
    def test_weak_password_rejected(self):
        email = f"TEST_weak_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "nome": "Weak Tester", "email": email, "password": "abcdef",
            "role": "influencer", "aceita_termos": True,
        })
        if r.status_code == 429:
            pytest.skip("register rate limit (5/hour) exhausted — behavior verified in prior run")
        assert r.status_code == 400
        body = r.json()
        detail = body.get("detail", "") if isinstance(body, dict) else str(body)
        assert "8" in detail and ("letra" in detail.lower() or "letters" in detail.lower())
        assert "número" in detail.lower() or "digit" in detail.lower() or "numero" in detail.lower()

    def test_valid_password_registers(self):
        email = f"TEST_iter31_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "nome": "Iter31 Tester", "email": email, "password": "Teste1234",
            "role": "influencer", "aceita_termos": True,
        })
        if r.status_code == 429:
            pytest.skip("register rate limit (5/hour) exhausted — behavior verified in prior run")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("token")
        assert body["user"]["email"] == email.lower()
        # Store email so main agent knows which to delete
        with open("/tmp/iter31_test_user.txt", "w") as f:
            f.write(email)
        print(f"Created test user: {email}")


# --- WebSocket auth via first message ---
class TestWebSocket:
    @pytest.mark.asyncio
    async def test_ws_auth_success(self, admin_token):
        async with websockets.connect(WS_URL, open_timeout=10) as ws:
            await ws.send(json.dumps({"type": "auth", "token": admin_token}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert data.get("tipo") == "ligado"

    @pytest.mark.asyncio
    async def test_ws_invalid_token_closes_4401(self):
        try:
            async with websockets.connect(WS_URL, open_timeout=10) as ws:
                await ws.send(json.dumps({"type": "auth", "token": "invalid.jwt.token"}))
                # server should close
                try:
                    while True:
                        await asyncio.wait_for(ws.recv(), timeout=5)
                except websockets.ConnectionClosed as e:
                    assert e.code == 4401
                    return
                pytest.fail("Connection was not closed")
        except websockets.ConnectionClosed as e:
            assert e.code == 4401

    @pytest.mark.asyncio
    async def test_ws_no_auth_timeout_closes_4401(self):
        try:
            async with websockets.connect(WS_URL, open_timeout=10) as ws:
                try:
                    while True:
                        await asyncio.wait_for(ws.recv(), timeout=12)
                except websockets.ConnectionClosed as e:
                    assert e.code == 4401
                    return
                pytest.fail("Connection was not closed")
        except websockets.ConnectionClosed as e:
            assert e.code == 4401


# --- Message length limit ---
class TestMessageLength:
    def test_long_message_rejected(self, admin_headers):
        # find or create a conversation
        r = requests.get(f"{BASE_URL}/api/messages/conversations", headers=admin_headers)
        assert r.status_code == 200
        convs = r.json()
        if convs:
            cid = convs[0]["id"]
        else:
            # try to create with any allowed contact
            cr = requests.get(f"{BASE_URL}/api/messages/contacts", headers=admin_headers)
            assert cr.status_code == 200
            contacts = cr.json()
            if not contacts:
                pytest.skip("no contacts available to create conversation")
            pid = contacts[0]["id"]
            cc = requests.post(f"{BASE_URL}/api/messages/conversations", headers=admin_headers,
                               json={"participant_id": pid})
            assert cc.status_code == 200
            cid = cc.json()["id"]
        long_text = "a" * 2001
        r = requests.post(f"{BASE_URL}/api/messages/conversations/{cid}", headers=admin_headers,
                          json={"text": long_text})
        assert r.status_code == 400
        assert "2000" in r.text or "longa" in r.text.lower()


# --- Diretor apply-correction endpoint ---
class TestDiretorApply:
    def test_aplicar_nonexistent_returns_404(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/diretor/acoes/nonexistent-id-xyz/aplicar", headers=admin_headers)
        assert r.status_code == 404

    def test_aplicar_as_influencer_returns_403(self):
        # register a fresh influencer OR reuse the last-created influencer
        try:
            with open("/tmp/iter31_test_user.txt") as f:
                email = f.read().strip()
            login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "Teste1234"})
            if login.status_code != 200:
                pytest.skip(f"cannot login as test influencer: {login.text}")
            infl_token = login.json()["token"]
        except FileNotFoundError:
            pytest.skip("no test influencer available")
        h = {"Authorization": f"Bearer {infl_token}"}
        r2 = requests.post(f"{BASE_URL}/api/diretor/acoes/any-id/aplicar", headers=h)
        assert r2.status_code == 403

    def test_propose_approve_apply_flow(self, admin_headers):
        # Get latest audit
        r = requests.get(f"{BASE_URL}/api/diretor/auditoria", headers=admin_headers)
        assert r.status_code == 200
        audit = r.json()
        if not audit or not audit.get("achados"):
            pytest.skip("No existing audit findings")
        # Pick a finding with non-empty diff AND no acao_id yet
        finding = next((f for f in audit["achados"] if f.get("diff", "").strip() and not f.get("acao_id")), None)
        if not finding:
            pytest.skip("No unproposed finding with a non-empty diff")
        pr = requests.post(
            f"{BASE_URL}/api/diretor/auditoria/{audit['id']}/propor/{finding['id']}",
            headers=admin_headers,
        )
        assert pr.status_code == 200, pr.text
        acao_id = pr.json()["id"]
        # Approve
        ap = requests.post(f"{BASE_URL}/api/diretor/acoes/{acao_id}/aprovar", headers=admin_headers)
        assert ap.status_code == 200, ap.text
        # Apply
        apl = requests.post(f"{BASE_URL}/api/diretor/acoes/{acao_id}/aplicar", headers=admin_headers, timeout=300)
        assert apl.status_code == 200, apl.text
        body = apl.json()
        assert body.get("status") in ("aplicada", "falhou", "revertida"), body
        # shape check based on status
        if body["status"] == "aplicada":
            assert "ficheiros" in body and "verificacao" in body
            print(f"APPLIED FILES: {body['ficheiros']}")
        else:
            assert "etapa" in body and "erro" in body
        # Verify listing shows aplicacao field
        lst = requests.get(f"{BASE_URL}/api/diretor/acoes", headers=admin_headers, params={"status": "aprovada"})
        assert lst.status_code == 200
        found = next((a for a in lst.json() if a["id"] == acao_id), None)
        assert found is not None
        assert "aplicacao" in found
        # Double approve of same action → 404 (status is aprovada, not pendente)
        dup = requests.post(f"{BASE_URL}/api/diretor/acoes/{acao_id}/aprovar", headers=admin_headers)
        assert dup.status_code in (404, 409)
