# Iter41: partner photo upload, public coupon avatar, P5 config regression
import os, base64, pytest, requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PNG = "data:image/png;base64," + base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cf00000301010018dd8db00000000049454e44ae426082")).decode()


def _login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login {email} -> {r.status_code}")
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture(scope="module")
def partner():
    return _login("parceiro.exemplo@club.pt", "parceiro123")


@pytest.fixture(scope="module")
def influencer():
    return _login("influencer.exemplo@club.pt", "influencer123")


def test_photo_upload_ok(partner):
    r = requests.post(f"{BASE}/partner/foto", json={"foto": PNG}, headers=partner, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_public_coupon_avatar(partner):
    r = requests.get(f"{BASE}/public/coupon/CLUB-10", timeout=20)
    assert r.status_code == 200
    assert str(r.json().get("avatar", "")).startswith("data:image")


def test_photo_invalid_400(partner):
    r = requests.post(f"{BASE}/partner/foto", json={"foto": "x" * 64}, headers=partner, timeout=20)
    assert r.status_code == 400


def test_photo_influencer_403(influencer):
    r = requests.post(f"{BASE}/partner/foto", json={"foto": PNG}, headers=influencer, timeout=20)
    assert r.status_code == 403


def test_p5_config():
    r = requests.get(f"{BASE}/public/p5/config", timeout=20)
    assert r.status_code == 200
    print(r.json())
