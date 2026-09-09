import os
import time
import requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
ADMIN = ("faellt@gmail.com", "Robson2026!")
PARTNER = ("parceiro.exemplo@club.pt", "parceiro123")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _ensure_partner_user(admin_token):
    # try login; if fails, create + link to Parceiro Exemplo
    r = _login(*PARTNER)
    if r.status_code == 200:
        return r.json()
    # find or create
    users = requests.get(f"{API}/admin/usuarios", headers=_auth(admin_token)).json()
    u = next((x for x in users if x["email"] == PARTNER[0]), None)
    if not u:
        r = requests.post(f"{API}/admin/usuarios", headers=_auth(admin_token), json={
            "nome": "Parceiro Exemplo", "email": PARTNER[0], "role": "partner", "password": PARTNER[1]})
        assert r.status_code in (200, 201), r.text
        u = r.json()
    else:
        requests.put(f"{API}/admin/usuarios/{u['id']}", headers=_auth(admin_token), json={"password": PARTNER[1]})
    # link to partner named 'Parceiro Exemplo'
    partners = requests.get(f"{API}/admin/parceiros", headers=_auth(admin_token)).json()
    pex = next((p for p in partners if "Parceiro Exemplo" in p.get("nome", "")), None) or (partners[0] if partners else None)
    if pex and u.get("partner_id") != pex["id"]:
        requests.put(f"{API}/admin/usuarios/{u['id']}", headers=_auth(admin_token), json={"partner_id": pex["id"]})
    r = _login(*PARTNER)
    assert r.status_code == 200, r.text
    return r.json()


# --- Auth ---
def test_admin_login():
    r = _login(*ADMIN)
    assert r.status_code == 200, r.text
    assert r.json().get("token")


def test_partner_login_and_setup():
    ar = _login(*ADMIN); assert ar.status_code == 200
    data = _ensure_partner_user(ar.json()["token"])
    assert data["user"]["role"] == "partner"


# --- Partner Connect ---
def test_connect_onboard_returns_available_false_when_connect_not_active():
    pr = _login(*PARTNER); assert pr.status_code == 200, pr.text
    token = pr.json()["token"]
    r = requests.post(f"{API}/partner/connect/onboard", headers=_auth(token),
                      json={"origin_url": BASE})
    assert r.status_code == 200, r.text
    j = r.json()
    # Either not-available (Connect not signed up) OR available (already onboarded)
    assert "available" in j
    if j["available"] is False:
        assert "Connect" in (j.get("reason") or "")


def test_connect_status_partner():
    pr = _login(*PARTNER); token = pr.json()["token"]
    r = requests.get(f"{API}/partner/connect/status", headers=_auth(token))
    assert r.status_code == 200, r.text
    j = r.json()
    assert "connected" in j and "charges_enabled" in j


def test_connect_endpoints_forbid_non_partner():
    ar = _login(*ADMIN); token = ar.json()["token"]
    r = requests.post(f"{API}/partner/connect/onboard", headers=_auth(token), json={"origin_url": BASE})
    assert r.status_code == 403
    r = requests.get(f"{API}/partner/connect/status", headers=_auth(token))
    assert r.status_code == 403


# --- Public pay with email ---
def test_public_pay_with_email_and_status():
    r = requests.post(f"{API}/public/pay", json={"code": "CLUB-10", "amount": 50, "origin_url": BASE,
                                                 "email": "cliente.test@club.pt"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "checkout_url" in j and "session_id" in j
    assert j["to_pay"] == 45.0
    assert j["discount"] == 5.0
    assert j["split"] is False
    sid = j["session_id"]

    st = requests.get(f"{API}/payments/status/{sid}")
    assert st.status_code == 200, st.text
    s = st.json()
    assert s["payment_status"] == "pending"
    assert s["kind"] == "coupon_pay"
    assert s["gross_amount"] == 50.0
    assert s["discount"] == 5.0
    assert s["coupon"] == "CLUB-10"


def test_public_pay_email_optional():
    r = requests.post(f"{API}/public/pay", json={"code": "CLUB-10", "amount": 30, "origin_url": BASE})
    assert r.status_code == 200
    assert "session_id" in r.json()


# --- Regression: admin partners list ---
def test_admin_partners_list():
    ar = _login(*ADMIN); token = ar.json()["token"]
    r = requests.get(f"{API}/admin/parceiros", headers=_auth(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
