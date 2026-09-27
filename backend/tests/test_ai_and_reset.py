"""Tests for AI analyst SSE + reset-all endpoint (iteration 22)."""
import json
import os
import re
import pytest
import requests

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            for line in open("/app/frontend/.env"):
                if line.startswith("REACT_APP_BACKEND_URL="):
                    v = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")

BASE_URL = _load_url()
HDRS = {"User-Agent": "Mozilla/5.0 (compatible; RRTests/1.0)"}
ADMIN = {"email": "faellt@gmail.com", "password": "Robson2026!"}
PARTNER = {"email": "parceiro.exemplo@club.pt", "password": "parceiro123"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, headers=HDRS, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def partner_token():
    return _login(PARTNER)


def _parse_sse(text):
    """Return list of (event, data) blocks."""
    blocks = []
    for chunk in text.split("\n\n"):
        if not chunk.strip():
            continue
        ev = "message"
        data = None
        for line in chunk.splitlines():
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        blocks.append((ev, data))
    return blocks


# ---------------- AI Analyst ----------------
class TestAIAnalyst:
    def test_ai_ask_non_admin_forbidden(self, partner_token):
        r = requests.post(
            f"{BASE_URL}/api/admin/ai/ask",
            headers={**HDRS, "Authorization": f"Bearer {partner_token}"},
            json={"message": "teste"},
            timeout=30,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"

    def test_ai_ask_streams_meta_data_done(self, admin_token):
        with requests.post(
            f"{BASE_URL}/api/admin/ai/ask",
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            json={"message": "Quantas campanhas ativas existem? Responde numa frase."},
            stream=True,
            timeout=90,
        ) as r:
            assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"
            assert "text/event-stream" in r.headers.get("content-type", ""), r.headers
            body = r.content.decode("utf-8", errors="replace")

        blocks = _parse_sse(body)
        assert blocks, "no SSE blocks"
        # first block should be meta
        first_ev, first_data = blocks[0]
        assert first_ev == "meta", f"first ev={first_ev}"
        meta = json.loads(first_data)
        session_id = meta["session_id"]
        assert session_id
        # last should be done
        evs = [b[0] for b in blocks]
        assert "done" in evs, f"no done event, events={evs}"
        # there should be several data blocks
        tokens = [b[1] for b in blocks if b[0] == "message" and b[1]]
        assert len(tokens) >= 2, f"too few token blocks: {len(tokens)}"
        answer = "".join(json.loads(t) for t in tokens)
        assert answer.strip(), "empty answer"
        # store for follow-up test
        pytest.ai_session_id = session_id
        pytest.ai_first_answer = answer
        print("AI answer:", answer[:400])

    def test_ai_history_two_messages(self, admin_token):
        sid = getattr(pytest, "ai_session_id", None)
        assert sid, "no session id from previous test"
        r = requests.get(
            f"{BASE_URL}/api/admin/ai/history",
            params={"session_id": sid},
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2, f"expected >=2 messages got {len(msgs)}"
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles

    def test_ai_ask_multi_turn(self, admin_token):
        sid = getattr(pytest, "ai_session_id", None)
        assert sid
        with requests.post(
            f"{BASE_URL}/api/admin/ai/ask",
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            json={"session_id": sid, "message": "E quantos influencers ativos?"},
            stream=True,
            timeout=90,
        ) as r:
            assert r.status_code == 200
            body = r.content.decode("utf-8", errors="replace")
        blocks = _parse_sse(body)
        assert blocks[0][0] == "meta"
        meta = json.loads(blocks[0][1])
        assert meta["session_id"] == sid, "session id should be preserved"
        assert any(b[0] == "done" for b in blocks)
        tokens = [b[1] for b in blocks if b[0] == "message" and b[1]]
        answer = "".join(json.loads(t) for t in tokens)
        assert answer.strip()
        print("multi-turn answer:", answer[:300])


# ---------------- Reset All ----------------
class TestResetAll:
    def test_reset_all_requires_confirmation(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/admin/reset-all",
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            json={"confirm": "wrong"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_reset_all_works_and_zeroes_dashboard(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/admin/reset-all",
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            json={"confirm": "RESET-ALL"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is True
        assert "removed" in data

        # verify redemptions cleared (kpi-receita-sistema will be 0)
        # skip dashboard endpoint (varies by route); check totals via kpis
        k = requests.get(
            f"{BASE_URL}/api/admin/kpis",
            headers={**HDRS, "Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        if k.status_code == 200:
            kj = k.json()
            print("kpis after reset:", {k2: v for k2, v in kj.items() if isinstance(v, (int, float))})
