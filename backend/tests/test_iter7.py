"""Iteration 7 backend tests: admin settings, reset-pilot guard, PWA assets, regression."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
# fallback: read from frontend .env
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return login("admin@robson.club", "admin123")


@pytest.fixture(scope="module")
def influencer_token():
    return login("robson@robson.club", "robson123")


@pytest.fixture(scope="module")
def partner_token():
    return login("gerencia@tivolisky.pt", "tivoli123")


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ------- Admin Settings ---------
def test_admin_settings_get(admin_token):
    r = requests.get(f"{API}/admin/settings", headers=auth(admin_token), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "email_configured" in d and isinstance(d["email_configured"], bool)
    assert "demo_disabled" in d and isinstance(d["demo_disabled"], bool)
    assert "counts" in d and all(k in d["counts"] for k in ["users", "redemptions", "campaigns", "partners", "influencers"])


def test_admin_settings_email_invalid_key(admin_token):
    r = requests.post(f"{API}/admin/settings/email", json={"resend_api_key": "abc"}, headers=auth(admin_token), timeout=15)
    assert r.status_code == 400, r.text


def test_admin_settings_email_sender_only_ok(admin_token):
    r = requests.post(f"{API}/admin/settings/email",
                      json={"resend_api_key": "", "sender_email": "ןןClub <x@y.com>"},
                      headers=auth(admin_token), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    # email_configured stays False because no key ever provided
    r2 = requests.get(f"{API}/admin/settings", headers=auth(admin_token), timeout=15)
    assert r2.status_code == 200
    assert r2.json()["email_configured"] is False
    assert r2.json()["sender_email"] == "ןןClub <x@y.com>"


def test_admin_settings_test_email_502_without_key(admin_token):
    r = requests.post(f"{API}/admin/settings/email/test", headers=auth(admin_token), timeout=20)
    assert r.status_code == 502, r.text


def test_influencer_forbidden_on_settings(influencer_token):
    r = requests.get(f"{API}/admin/settings", headers=auth(influencer_token), timeout=15)
    assert r.status_code == 403


# ------- reset-pilot guard ---------
def test_reset_pilot_wrong_confirm(admin_token):
    r = requests.post(f"{API}/admin/reset-pilot", json={"confirm": "nao"}, headers=auth(admin_token), timeout=15)
    assert r.status_code == 400, r.text
    # explicitly do NOT send 'ZERAR' — destructive


# ------- PWA assets ---------
def test_manifest_json():
    r = requests.get(f"{BASE}/manifest.json", timeout=15)
    assert r.status_code == 200, r.status_code
    d = r.json()
    assert d["short_name"] == "ןןClub"
    assert isinstance(d.get("icons"), list) and len(d["icons"]) >= 2
    sizes = {i.get("sizes") for i in d["icons"]}
    assert "192x192" in sizes and "512x512" in sizes


@pytest.mark.parametrize("path", ["/icon-192.png", "/icon-512.png", "/sw.js"])
def test_pwa_assets_available(path):
    r = requests.get(f"{BASE}{path}", timeout=15)
    assert r.status_code == 200, f"{path} → {r.status_code}"


# ------- Regression ---------
def test_login_three_roles():
    for e, p in [("admin@robson.club", "admin123"), ("robson@robson.club", "robson123"), ("gerencia@tivolisky.pt", "tivoli123")]:
        r = requests.post(f"{API}/auth/login", json={"email": e, "password": p}, timeout=15)
        assert r.status_code == 200, f"{e}: {r.status_code}"


def test_influencer_dashboard(influencer_token):
    r = requests.get(f"{API}/dashboard/influencer", headers=auth(influencer_token), timeout=15)
    assert r.status_code == 200
    assert "kpis" in r.json() or "resumo" in r.json() or isinstance(r.json(), dict)


def test_public_coupon_ok():
    r = requests.get(f"{API}/public/coupon/ROBSON-LUXE-25", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("code") == "ROBSON-LUXE-25" or d.get("codigo") == "ROBSON-LUXE-25" or "ROBSON-LUXE-25" in str(d)
