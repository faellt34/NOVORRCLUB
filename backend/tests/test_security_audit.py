"""Tests for /api/diretor/auditoria - Security Audit."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
HEADERS_UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "faellt@gmail.com", "password": "Robson2026!"}, headers=HEADERS_UA)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def partner_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "parceiro.exemplo@club.pt", "password": "parceiro123"}, headers=HEADERS_UA)
    if r.status_code != 200:
        pytest.skip("partner login failed")
    return r.json()["token"]


@pytest.fixture(scope="module")
def latest_audit(admin_token):
    h = {**HEADERS_UA, "Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE}/api/diretor/auditoria", headers=h, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    if not data or not data.get("achados"):
        # Run audit only if empty
        r2 = requests.post(f"{BASE}/api/diretor/auditoria", headers=h, timeout=300)
        assert r2.status_code == 200, r2.text
        data = r2.json()
    return data


def test_get_latest_audit_has_findings(latest_audit):
    a = latest_audit
    assert "id" in a and a["id"]
    assert "timestamp" in a
    assert isinstance(a.get("achados"), list) and len(a["achados"]) > 0
    assert isinstance(a.get("resumo"), dict)
    for k in ("alta", "media", "baixa"):
        assert k in a["resumo"]
    f0 = a["achados"][0]
    for k in ("id", "ficheiro", "severidade", "titulo", "descricao", "correcao"):
        assert k in f0, f"missing {k} in finding"
    assert f0["severidade"] in ("alta", "media", "baixa")


def test_propose_from_finding_creates_pending_action(admin_token, latest_audit):
    h = {**HEADERS_UA, "Authorization": f"Bearer {admin_token}"}
    audit_id = latest_audit["id"]
    f = latest_audit["achados"][0]
    r = requests.post(f"{BASE}/api/diretor/auditoria/{audit_id}/propor/{f['id']}", headers=h, timeout=30)
    assert r.status_code == 200, r.text
    action = r.json()
    assert action.get("tipo_acao") == "propor_correcao"
    assert action.get("status") == "pendente"
    assert action.get("dados_json", {}).get("ficheiro") == f["ficheiro"]
    action_id = action["id"]

    # verify present in pending list
    r2 = requests.get(f"{BASE}/api/diretor/acoes?status=pendente", headers=h, timeout=30)
    assert r2.status_code == 200
    ids = [x.get("id") for x in r2.json()]
    assert action_id in ids


def test_invalid_finding_id_returns_404(admin_token, latest_audit):
    h = {**HEADERS_UA, "Authorization": f"Bearer {admin_token}"}
    r = requests.post(f"{BASE}/api/diretor/auditoria/{latest_audit['id']}/propor/nonexistent-finding-xyz", headers=h, timeout=30)
    assert r.status_code == 404


def test_partner_forbidden_on_get_auditoria(partner_token):
    h = {**HEADERS_UA, "Authorization": f"Bearer {partner_token}"}
    r = requests.get(f"{BASE}/api/diretor/auditoria", headers=h, timeout=30)
    assert r.status_code == 403
