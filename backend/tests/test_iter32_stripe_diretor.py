"""Iteration 32: Stripe status endpoints + Diretor credit control tests."""
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

def _read_frontend_env():
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                return ln.split("=", 1)[1].strip().strip('"').rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL missing")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()
BASE_URL = BASE_URL.rstrip("/")
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"
ADMIN_EMAIL = "faellt@gmail.com"
ADMIN_PASSWORD = "Robson2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---- Payments config (public) ----
def test_payments_config_public():
    r = requests.get(f"{BASE_URL}/api/payments/config", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] in ("test", "live")
    assert isinstance(d["available"], bool)
    assert "connect_enabled" in d
    print(f"payments/config: {d}")


# ---- Admin Stripe status ----
def test_admin_stripe_status_as_admin(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/stripe/status", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert "config" in d and "steps" in d and "done" in d and "total" in d
    assert d["total"] == 5
    ids = [s["id"] for s in d["steps"]]
    assert set(ids) == {"chave", "modo", "webhook", "connect", "parceiros"}
    for s in d["steps"]:
        assert "ok" in s and isinstance(s["ok"], bool)
        assert "label" in s and "action" in s
    print(f"stripe status done/total={d['done']}/{d['total']}, ids={ids}")


def test_admin_stripe_status_forbidden_no_auth():
    r = requests.get(f"{BASE_URL}/api/admin/stripe/status", timeout=15)
    assert r.status_code in (401, 403)


# ---- Diretor uso ----
def test_diretor_uso_get(admin_headers):
    r = requests.get(f"{BASE_URL}/api/diretor/uso", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ("hoje", "limite", "por_origem", "custo_auditoria"):
        assert k in d, f"missing key {k}"
    assert isinstance(d["por_origem"], dict)


def test_diretor_uso_limite_too_low(admin_headers):
    r = requests.post(f"{BASE_URL}/api/diretor/uso/limite", headers=admin_headers, json={"limite_diario": 3}, timeout=15)
    assert r.status_code == 400


def test_diretor_uso_limite_set_80_and_verify(admin_headers):
    r = requests.post(f"{BASE_URL}/api/diretor/uso/limite", headers=admin_headers, json={"limite_diario": 80}, timeout=15)
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/diretor/uso", headers=admin_headers, timeout=15).json()
    assert g["limite"] == 80


# ---- Daily cap enforcement via MongoDB seed ----
@pytest.mark.asyncio
async def test_daily_cap_returns_429(admin_headers):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    try:
        # Set limit to 5
        r = requests.post(f"{BASE_URL}/api/diretor/uso/limite", headers=admin_headers, json={"limite_diario": 5}, timeout=15)
        assert r.status_code == 200

        hoje = datetime.now(timezone.utc).date().isoformat()
        # remove any pre-existing 'teste' docs first
        await db.llm_usage.delete_many({"origem": "teste"})
        # Insert enough docs to exhaust: current usage + 5 test docs >= 5
        current = await db.llm_usage.count_documents({"dia": hoje})
        need = max(0, 5 - current) + 1  # push over
        docs = [{"id": f"llm-teste-{i}", "dia": hoje, "origem": "teste", "timestamp": datetime.now(timezone.utc).isoformat()} for i in range(need)]
        if docs:
            await db.llm_usage.insert_many(docs)

        # POST /api/diretor/conversar → 429
        r = requests.post(f"{BASE_URL}/api/diretor/conversar", headers=admin_headers, json={"mensagem": "olá"}, timeout=20)
        assert r.status_code == 429, f"expected 429 got {r.status_code} {r.text[:200]}"
        assert "Limite diário" in r.json().get("detail", "")

        # POST /api/diretor/auditoria → 429
        r = requests.post(f"{BASE_URL}/api/diretor/auditoria", headers=admin_headers, timeout=20)
        assert r.status_code == 429, f"expected 429 got {r.status_code} {r.text[:200]}"
    finally:
        # Cleanup: remove test docs and restore limit
        await db.llm_usage.delete_many({"origem": "teste"})
        client.close()
        requests.post(f"{BASE_URL}/api/diretor/uso/limite", headers=admin_headers, json={"limite_diario": 60}, timeout=15)


def test_restore_limit_60(admin_headers):
    r = requests.post(f"{BASE_URL}/api/diretor/uso/limite", headers=admin_headers, json={"limite_diario": 60}, timeout=15)
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/diretor/uso", headers=admin_headers, timeout=15).json()
    assert g["limite"] == 60
