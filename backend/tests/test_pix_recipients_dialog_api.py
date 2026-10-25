# Pix recipients diagnostic/reconcile + P5 charges diagnostic + campaign currency (iteration 39)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CAMP = "c-be2c66f79d"
PARTNER = "p-3657b48e8e"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "faellt@gmail.com", "password": "Robson2026!"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# Campaign list includes currency
def test_campanhas_currency(h):
    r = requests.get(f"{BASE_URL}/api/admin/campanhas", headers=h)
    assert r.status_code == 200
    items = r.json()
    assert all(i.get("currency") in ("eur", "brl") for i in items)
    br = [i for i in items if i["id"] == CAMP]
    assert br and br[0]["currency"] == "brl" and br[0]["cupom"] == "BRTEST-01"
    assert br[0]["parceiro"] == "Loja BR Teste"


def test_p5_charges_empty(h):
    r = requests.get(f"{BASE_URL}/api/admin/p5/charges/{CAMP}", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["campaign_id"] == CAMP and d["charges"] == []


def test_recipients_diagnostic(h):
    r = requests.get(f"{BASE_URL}/api/admin/pix/recipients/{CAMP}", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["cupom"] == "BRTEST-01"
    rec = d["recipients"]
    assert rec["partner"]["nome"] == "Loja BR Teste"
    assert rec["partner"]["bloqueio"] == "sem pix_stripe_account_id"
    assert rec["partner"]["pix_account"] is None
    assert rec["influencer"]["nome"] == "Influencer Exemplo"
    assert rec["influencer"]["bloqueio"] == "sem pix_stripe_account_id"
    assert "_id" not in d and "_id" not in rec["partner"]


def test_recipients_404(h):
    assert requests.get(f"{BASE_URL}/api/admin/pix/recipients/c-nope", headers=h).status_code == 404
    assert requests.post(f"{BASE_URL}/api/admin/pix/recipients/c-nope/reconcile", headers=h).status_code == 404


def test_reconcile_sem_conta(h):
    r = requests.post(f"{BASE_URL}/api/admin/pix/recipients/{CAMP}/reconcile", headers=h)
    assert r.status_code == 200
    assert r.json()["result"] == {"partner": "sem conta", "influencer": "sem conta"}


@pytest.mark.parametrize("method,path", [
    ("get", f"/api/admin/pix/recipients/{CAMP}"),
    ("post", f"/api/admin/pix/recipients/{CAMP}/reconcile"),
    ("get", f"/api/admin/p5/charges/{CAMP}"),
    ("get", "/api/admin/campanhas"),
])
def test_unauth(method, path):
    r = getattr(requests, method)(f"{BASE_URL}{path}")
    assert r.status_code in (401, 403)
    r = getattr(requests, method)(f"{BASE_URL}{path}", headers={"Authorization": "Bearer invalid"})
    assert r.status_code in (401, 403)


def test_non_admin_role_forbidden():
    # partner example user (may not exist after pilot reset)
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "parceiro.exemplo@club.pt", "password": "parceiro123"})
    if r.status_code != 200:
        pytest.skip("no non-admin user available")
    hh = {"Authorization": f"Bearer {r.json()['token']}"}
    assert requests.get(f"{BASE_URL}/api/admin/pix/recipients/{CAMP}", headers=hh).status_code == 403
    assert requests.get(f"{BASE_URL}/api/admin/p5/charges/{CAMP}", headers=hh).status_code == 403
