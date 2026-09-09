"""Iter 8 backend tests: public coupon pay + partner IBAN + admin partner IBAN edit."""
import os
import pytest
import requests
from pathlib import Path

def _load_env():
    for p in [Path("/app/frontend/.env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ADMIN = ("faellt@gmail.com", "Robson2026!")
PARTNER_EMAIL = "parceiro.exemplo@test.pt"
PARTNER_PWD = "parceiro123"


def _login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(*ADMIN)}"}


@pytest.fixture(scope="module")
def partner_id(admin_headers):
    r = requests.get(f"{BASE}/admin/parceiros", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    for p in r.json():
        if p["nome"].strip().lower() == "parceiro exemplo":
            return p["id"]
    pytest.skip("Parceiro Exemplo not found in seed")


@pytest.fixture(scope="module")
def partner_user_and_token(admin_headers, partner_id):
    # Find or create user
    users = requests.get(f"{BASE}/admin/usuarios", headers=admin_headers, timeout=30).json()
    u = next((x for x in users if x["email"] == PARTNER_EMAIL), None)
    if not u:
        r = requests.post(f"{BASE}/admin/usuarios", headers=admin_headers, json={
            "nome": "Parceiro Exemplo",
            "email": PARTNER_EMAIL,
            "papel": "Parceiro",
            "status": "Ativo",
            "password": PARTNER_PWD,
        }, timeout=30)
        assert r.status_code in (200, 201), r.text
        u = r.json()
    # Link partner_id
    r = requests.put(f"{BASE}/admin/usuarios/{u['id']}", headers=admin_headers,
                     json={"partner_id": partner_id}, timeout=30)
    assert r.status_code == 200, r.text
    tok = _login(PARTNER_EMAIL, PARTNER_PWD)
    return u, tok


# ---- Public /public/pay ----

def test_public_pay_invalid_coupon():
    r = requests.post(f"{BASE}/public/pay", json={"code": "NAO-EXISTE-XYZ", "amount": 100,
                                                  "origin_url": "https://example.com"}, timeout=30)
    assert r.status_code == 404


def test_public_pay_zero_amount():
    r = requests.post(f"{BASE}/public/pay", json={"code": "CLUB-10", "amount": 0,
                                                  "origin_url": "https://example.com"}, timeout=30)
    assert r.status_code == 400


def test_public_pay_ok_and_status():
    r = requests.post(f"{BASE}/public/pay", json={"code": "CLUB-10", "amount": 100,
                                                  "origin_url": "https://example.com"}, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["to_pay"] == 90.0
    assert data["discount"] == 10.0
    assert data["checkout_url"].startswith("https://checkout.stripe.com")
    sid = data["session_id"]
    # Poll status
    r2 = requests.get(f"{BASE}/payments/status/{sid}", timeout=30)
    assert r2.status_code == 200, r2.text
    s = r2.json()
    assert s["kind"] == "coupon_pay"
    assert s["payment_status"] == "pending"
    assert s["coupon"] == "CLUB-10"


# ---- Partner IBAN ----

def test_partner_iban_valid_and_dashboard(partner_user_and_token):
    _, tok = partner_user_and_token
    h = {"Authorization": f"Bearer {tok}"}
    iban = "PT50000201231234567890154"
    r = requests.post(f"{BASE}/partner/iban", headers=h, json={"iban": iban, "titular": "Parceiro Exemplo"}, timeout=30)
    assert r.status_code == 200, r.text
    d = requests.get(f"{BASE}/dashboard/partner", headers=h, timeout=30).json()
    assert d["partner"]["iban"] == iban
    assert "online_paid" in d["totals"]


def test_partner_iban_invalid(partner_user_and_token):
    _, tok = partner_user_and_token
    r = requests.post(f"{BASE}/partner/iban", headers={"Authorization": f"Bearer {tok}"},
                      json={"iban": "123"}, timeout=30)
    assert r.status_code == 400


def test_partner_iban_forbidden_for_admin(admin_headers):
    r = requests.post(f"{BASE}/partner/iban", headers=admin_headers,
                      json={"iban": "PT50000201231234567890154"}, timeout=30)
    assert r.status_code == 403


# ---- Admin edit partner iban ----

def test_admin_edit_partner_iban(admin_headers, partner_id):
    iban = "PT50000201231234567890154"
    r = requests.put(f"{BASE}/admin/parceiros/{partner_id}", headers=admin_headers,
                     json={"iban": iban}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("iban") == iban
