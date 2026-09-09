"""Iteration 6 — Register (influencer/partner) + Public Coupon + Influencer claims KPI."""
import os
import uuid
from pathlib import Path

import pytest
import requests

for line in Path("/app/frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        os.environ.setdefault("BASE_URL", line.split("=", 1)[1].strip())
BASE = os.environ["BASE_URL"].rstrip("/") + "/api"

ADMIN = ("admin@robson.club", "admin123")
ROBSON = ("robson@robson.club", "robson123")
TIVOLI = ("gerencia@tivolisky.pt", "tivoli123")


def _login(email, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    return r


def H(t): return {"Authorization": f"Bearer {t}"}


def rand_email(prefix="test"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture(scope="module")
def admin_tok():
    r = _login(*ADMIN); assert r.status_code == 200; return r.json()["token"]


# ============ REGISTER INFLUENCER ============
class TestRegisterInfluencer:
    def test_influencer_register_success(self):
        email = rand_email("inf")
        body = {"nome": "Test Inf", "email": email, "password": "abc123", "role": "influencer",
                "handle": "novo.inf", "cidade": "Porto", "aceita_termos": True}
        r = requests.post(f"{BASE}/auth/register", json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["pending"] is False
        assert j["token"]
        assert j["user"]["role"] == "influencer"
        # /auth/me works
        me = requests.get(f"{BASE}/auth/me", headers=H(j["token"]))
        assert me.status_code == 200
        assert me.json()["email"] == email
        # login works
        r2 = _login(email, "abc123")
        assert r2.status_code == 200

    def test_password_too_short(self):
        r = requests.post(f"{BASE}/auth/register", json={
            "nome": "X", "email": rand_email(), "password": "abc", "role": "influencer",
            "handle": "h", "cidade": "Porto", "aceita_termos": True})
        assert r.status_code == 400

    def test_no_terms(self):
        r = requests.post(f"{BASE}/auth/register", json={
            "nome": "Xy", "email": rand_email(), "password": "abcdef", "role": "influencer",
            "handle": "h", "cidade": "Porto", "aceita_termos": False})
        assert r.status_code == 400

    def test_duplicate_email(self):
        email = rand_email("dup")
        b = {"nome": "Aa", "email": email, "password": "abcdef", "role": "influencer",
             "handle": "h", "cidade": "Porto", "aceita_termos": True}
        r1 = requests.post(f"{BASE}/auth/register", json=b)
        assert r1.status_code == 200
        r2 = requests.post(f"{BASE}/auth/register", json=b)
        assert r2.status_code == 409

    def test_invalid_role_admin(self):
        r = requests.post(f"{BASE}/auth/register", json={
            "nome": "Aa", "email": rand_email(), "password": "abcdef", "role": "admin",
            "aceita_termos": True})
        assert r.status_code == 400


# ============ REGISTER PARTNER ============
class TestRegisterPartner:
    def test_partner_register_pending_flow(self, admin_tok):
        email = rand_email("par")
        body = {"nome": "Rooftop Test", "email": email, "password": "abc123", "role": "partner",
                "categoria": "Rooftop", "cidade": "Lisboa", "aceita_termos": True}
        r = requests.post(f"{BASE}/auth/register", json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["pending"] is True
        assert "token" not in j or not j.get("token")
        # login → 403 aguarda aprovação
        r2 = _login(email, "abc123")
        assert r2.status_code == 403
        assert "aguarda aprovação" in r2.json().get("detail", "").lower() or "aguarda" in r2.json().get("detail", "").lower()

        # admin sees pending partner
        parts = requests.get(f"{BASE}/admin/parceiros", headers=H(admin_tok)).json()
        pending = [p for p in parts if p.get("nome") == "Rooftop Test" and p.get("status") == "Pendente"]
        assert pending, "Pending partner not found in admin list"
        pid = pending[0]["id"]

        # admin has notification of type "registo"
        notifs = requests.get(f"{BASE}/notifications", headers=H(admin_tok)).json()
        items = notifs.get("items", [])
        assert any(n.get("tipo") == "registo" for n in items), "admin has no 'registo' notification"

        # activate
        r3 = requests.put(f"{BASE}/admin/parceiros/{pid}", json={"status": "Ativo"}, headers=H(admin_tok))
        assert r3.status_code == 200
        assert r3.json()["status"] == "Ativo"

        # login now succeeds
        r4 = _login(email, "abc123")
        assert r4.status_code == 200
        tok = r4.json()["token"]
        # partner dashboard responds
        d = requests.get(f"{BASE}/dashboard/partner", headers=H(tok))
        assert d.status_code == 200
        # partner notification 'Conta ativada'
        pn = requests.get(f"{BASE}/notifications", headers=H(tok)).json()
        assert any("ativada" in (n.get("titulo", "") + n.get("mensagem", "")).lower() for n in pn.get("items", []))


# ============ PUBLIC COUPON ============
class TestPublicCoupon:
    def test_public_coupon_and_dedup(self):
        # fresh session to get first-time claim increment (but relies on IP+UA which is same)
        s = requests.Session()
        s.headers["User-Agent"] = f"pytest-ua-{uuid.uuid4().hex[:8]}"
        r1 = s.get(f"{BASE}/public/coupon/ROBSON-LUXE-25")
        assert r1.status_code == 200, r1.text
        j = r1.json()
        assert j["cupom"] == "ROBSON-LUXE-25"
        assert j["parceiro"] == "Tivoli Sky Bar"
        assert j["influencer"] == "Robson Oliveira"
        assert j["claims"] >= 1
        c1 = j["claims"]
        # second call → dedup: claims count should not increment
        r2 = s.get(f"{BASE}/public/coupon/ROBSON-LUXE-25")
        assert r2.status_code == 200
        assert r2.json()["claims"] == c1

    def test_not_found(self):
        r = requests.get(f"{BASE}/public/coupon/XPTO-DOES-NOT-EXIST")
        assert r.status_code == 404

    def test_influencer_kpi_claims(self):
        tok = _login(*ROBSON).json()["token"]
        d = requests.get(f"{BASE}/dashboard/influencer?period=30", headers=H(tok)).json()
        assert d["kpis"]["customers"] >= 1
        c1 = next((c for c in d["campaigns"] if c["id"] == "c1"), None)
        assert c1 is not None
        assert c1["claims"] >= 1


# ============ REGRESSION ============
class TestRegression:
    def test_login_three_roles(self):
        for creds in [ADMIN, ROBSON, TIVOLI]:
            r = _login(*creds)
            assert r.status_code == 200, f"{creds[0]} failed"

    def test_redemption_and_statements(self):
        tok = _login(*TIVOLI).json()["token"]
        r = requests.post(f"{BASE}/redemptions", json={
            "code": "ROBSON-LUXE-25", "amount": 88.50,
            "idempotency_key": f"iter6-{uuid.uuid4().hex}"}, headers=H(tok))
        assert r.status_code == 200, r.text
        assert r.json()["record"]["amount"] == 88.50
        # statements
        itok = _login(*ROBSON).json()["token"]
        s = requests.get(f"{BASE}/statements", headers=H(itok))
        assert s.status_code == 200
        assert isinstance(s.json(), list)
