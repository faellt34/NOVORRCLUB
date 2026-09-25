"""Iter21 — Reset-All + Test Mode (test-run, delete, clear-all) + WS venda_validada."""
import json
import os
import time
import threading
import pytest
import requests

try:
    from websockets.sync.client import connect as ws_connect
except Exception:
    ws_connect = None

def _load_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE = _load_env().rstrip("/")
UA = {"User-Agent": "Mozilla/5.0 iter21-tester"}
ADMIN = ("faellt@gmail.com", "Robson2026!")
INF = ("influencer.exemplo@club.pt", "influencer123")
PART = ("parceiro.exemplo@club.pt", "parceiro123")


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, headers=UA, timeout=15)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def inf_token():
    return _login(*INF)


@pytest.fixture(scope="module")
def partner_token():
    return _login(*PART)


def _h(tok):
    return {"Authorization": f"Bearer {tok}", **UA}


# --- reset-all ---
def test_reset_all_bad_confirm(admin_token):
    r = requests.post(f"{BASE}/api/admin/reset-all", json={"confirm": "nope"}, headers=_h(admin_token), timeout=15)
    assert r.status_code == 400


def test_reset_all_non_admin(partner_token):
    r = requests.post(f"{BASE}/api/admin/reset-all", json={"confirm": "RESET-ALL"}, headers=_h(partner_token), timeout=15)
    assert r.status_code == 403


def test_reset_all_ok_and_dashboard_zero(admin_token):
    r = requests.post(f"{BASE}/api/admin/reset-all", json={"confirm": "RESET-ALL"}, headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert "removed" in data
    # Dashboard totals now 0
    d = requests.get(f"{BASE}/api/dashboard/admin", headers=_h(admin_token), timeout=15).json()
    assert d["totals"]["revenue"] == 0, d
    assert d["funnel"]["clicks"] == 0, d
    # CLUB-10 campaign preserved
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers=_h(admin_token), timeout=15).json()
    cupons = [c.get("cupom") for c in camps]
    assert "CLUB-10" in cupons, cupons


# --- test-run ---
def _get_ids(admin_token):
    infs = requests.get(f"{BASE}/api/admin/influencers", headers=_h(admin_token), timeout=15).json()
    parts = requests.get(f"{BASE}/api/admin/parceiros", headers=_h(admin_token), timeout=15).json()
    assert infs and parts
    return infs[0]["id"], parts[0]["id"]


def test_test_run_non_admin(partner_token):
    r = requests.post(f"{BASE}/api/admin/test-run", json={"influencer_id": "x", "partner_id": "y", "valor": 50}, headers=_h(partner_token), timeout=15)
    assert r.status_code == 403


def test_test_run_creates_all_and_split(admin_token):
    inf_id, part_id = _get_ids(admin_token)
    r = requests.post(f"{BASE}/api/admin/test-run", json={"influencer_id": inf_id, "partner_id": part_id, "valor": 50}, headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cupom"].startswith("TEST-")
    assert data["split"] == {"restaurante": 37.5, "influencer": 2.5, "rrclub": 5.0, "stripe": 5.0}
    run_id = data["run_id"]
    # dashboard revenue 50
    d = requests.get(f"{BASE}/api/dashboard/admin", headers=_h(admin_token), timeout=15).json()
    assert d["totals"]["revenue"] == 50, d["totals"]
    # delete
    d2 = requests.delete(f"{BASE}/api/admin/test-run/{run_id}", headers=_h(admin_token), timeout=15).json()
    assert d2["ok"] is True
    assert d2["removed"]["campaigns"] == 1
    assert d2["removed"]["redemptions"] == 1
    # dashboard back to 0
    d3 = requests.get(f"{BASE}/api/dashboard/admin", headers=_h(admin_token), timeout=15).json()
    assert d3["totals"]["revenue"] == 0
    # CLUB-10 still there
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers=_h(admin_token), timeout=15).json()
    cupons = [c.get("cupom") for c in camps]
    assert "CLUB-10" in cupons
    assert not any(c.startswith("TEST-") for c in cupons if c)


# --- WS events during test-run ---
@pytest.mark.skipif(ws_connect is None, reason="websockets not available")
def test_test_run_ws_emits_all_events(admin_token):
    inf_id, part_id = _get_ids(admin_token)
    ws_url = BASE.replace("http", "ws") + f"/api/ws/dashboard?token={admin_token}"
    events = []
    stop = threading.Event()

    def _listen():
        try:
            with ws_connect(ws_url, open_timeout=10, close_timeout=5) as ws:
                ws.recv(timeout=3)  # ligado (may or may not send)
                while not stop.is_set():
                    try:
                        msg = ws.recv(timeout=1)
                        events.append(json.loads(msg))
                    except Exception:
                        continue
        except Exception as e:
            events.append({"error": str(e)})

    t = threading.Thread(target=_listen, daemon=True); t.start()
    time.sleep(1.5)
    r = requests.post(f"{BASE}/api/admin/test-run", json={"influencer_id": inf_id, "partner_id": part_id, "valor": 50}, headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    time.sleep(2.5)
    stop.set(); t.join(timeout=3)

    tipos = [e.get("tipo") for e in events]
    passos_ok = [e.get("passo") for e in events if e.get("tipo") == "teste_passo" and e.get("estado") == "ok"]
    assert set([1, 2, 3, 4, 5, 6]).issubset(set(passos_ok)), f"passos_ok={passos_ok} tipos={tipos}"
    assert "novo_clique" in tipos, tipos
    assert "qr_baixado" in tipos, tipos
    assert "venda_validada" in tipos, tipos
    venda = next(e for e in events if e.get("tipo") == "venda_validada")
    assert venda.get("valor") == 50
    assert "split_executado" in tipos

    # cleanup
    requests.delete(f"{BASE}/api/admin/test-run/{run_id}", headers=_h(admin_token), timeout=15)


# --- clear-all ---
def test_clear_all_bad_confirm(admin_token):
    r = requests.post(f"{BASE}/api/admin/test-run/clear-all", json={"confirm": "wrong"}, headers=_h(admin_token), timeout=15)
    assert r.status_code == 400


def test_clear_all_non_admin(partner_token):
    r = requests.post(f"{BASE}/api/admin/test-run/clear-all", json={"confirm": "LIMPAR"}, headers=_h(partner_token), timeout=15)
    assert r.status_code == 403


def test_clear_all_removes_multiple(admin_token):
    inf_id, part_id = _get_ids(admin_token)
    for _ in range(2):
        r = requests.post(f"{BASE}/api/admin/test-run", json={"influencer_id": inf_id, "partner_id": part_id, "valor": 50}, headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
    d = requests.get(f"{BASE}/api/dashboard/admin", headers=_h(admin_token), timeout=15).json()
    assert d["totals"]["revenue"] == 100, d["totals"]
    r = requests.post(f"{BASE}/api/admin/test-run/clear-all", json={"confirm": "LIMPAR"}, headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    rem = r.json()["removed"]
    assert rem["campaigns"] >= 2
    assert rem["redemptions"] >= 2
    d2 = requests.get(f"{BASE}/api/dashboard/admin", headers=_h(admin_token), timeout=15).json()
    assert d2["totals"]["revenue"] == 0
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers=_h(admin_token), timeout=15).json()
    cupons = [c.get("cupom") for c in camps]
    assert "CLUB-10" in cupons
    assert not any((c or "").startswith("TEST-") for c in cupons)
