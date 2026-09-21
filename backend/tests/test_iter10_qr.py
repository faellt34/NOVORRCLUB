"""Iteration 10 — QR coupon flow: public coupon + partner redemption."""
import os
import uuid
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["token"]


def test_public_coupon_club10():
    r = requests.get(f"{BASE_URL}/api/public/coupon/CLUB-10", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cupom"] == "CLUB-10"
    assert data["status"] == "Ativa"
    assert data["parceiro"]
    assert data["desconto"] > 0


def test_public_coupon_case_insensitive():
    r = requests.get(f"{BASE_URL}/api/public/coupon/club-10", timeout=30)
    assert r.status_code == 200
    assert r.json()["cupom"] == "CLUB-10"


def test_public_coupon_404():
    r = requests.get(f"{BASE_URL}/api/public/coupon/NOPE-XXXX", timeout=30)
    assert r.status_code == 404


def test_partner_redemption_and_idempotency():
    token = _login("parceiro.exemplo@club.pt", "parceiro123")
    h = {"Authorization": f"Bearer {token}"}
    idem = f"test-{uuid.uuid4()}"
    payload = {"code": "CLUB-10", "amount": 50, "idempotency_key": idem}
    r = requests.post(f"{BASE_URL}/api/redemptions", json=payload, headers=h, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["duplicate"] is False
    rec = body["record"]
    assert rec["coupon"] == "CLUB-10"
    assert rec["amount"] == 50.0
    assert rec["commission"] > 0
    # Idempotency — same key returns duplicate=True
    r2 = requests.post(f"{BASE_URL}/api/redemptions", json=payload, headers=h, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True


def test_partner_redemption_invalid_code():
    token = _login("parceiro.exemplo@club.pt", "parceiro123")
    h = {"Authorization": f"Bearer {token}"}
    payload = {"code": "NOPE-XXXX", "amount": 10, "idempotency_key": f"test-{uuid.uuid4()}"}
    r = requests.post(f"{BASE_URL}/api/redemptions", json=payload, headers=h, timeout=30)
    assert r.status_code == 404
