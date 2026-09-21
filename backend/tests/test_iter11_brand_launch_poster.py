"""Iteration 11: launch-check admin endpoint + campaign poster PDF."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN = ("faellt@gmail.com", "Robson2026!")
INFL = ("influencer.exemplo@club.pt", "influencer123")
PART = ("parceiro.exemplo@club.pt", "parceiro123")


def _login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_tok():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def infl_tok():
    try:
        return _login(*INFL)
    except AssertionError:
        # restore password via admin
        atok = _login(*ADMIN)
        h = {"Authorization": f"Bearer {atok}"}
        users = requests.get(f"{BASE}/api/admin/usuarios", headers=h, timeout=10).json()
        u = next(x for x in users if x["email"] == INFL[0])
        requests.put(f"{BASE}/api/admin/usuarios/{u['id']}", headers=h, json={"password": INFL[1]}, timeout=10)
        return _login(*INFL)


@pytest.fixture(scope="module")
def part_tok():
    try:
        return _login(*PART)
    except AssertionError:
        atok = _login(*ADMIN)
        h = {"Authorization": f"Bearer {atok}"}
        users = requests.get(f"{BASE}/api/admin/usuarios", headers=h, timeout=10).json()
        u = next(x for x in users if x["email"] == PART[0])
        requests.put(f"{BASE}/api/admin/usuarios/{u['id']}", headers=h, json={"password": PART[1]}, timeout=10)
        return _login(*PART)


# --- Launch check ---
def test_launch_check_admin(admin_tok):
    r = requests.get(f"{BASE}/api/admin/launch-check", headers={"Authorization": f"Bearer {admin_tok}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "done" in data and "total" in data
    assert data["total"] == 11, f"expected 11 items, got {data['total']}"
    assert len(data["items"]) == 11
    ids = {i["id"] for i in data["items"]}
    expected = {"domain", "https", "login", "campaign", "coupon_public", "scanner", "share", "email", "iban", "partners_iban", "stripe"}
    assert expected.issubset(ids), f"missing: {expected - ids}"
    # login should be green
    login_item = next(i for i in data["items"] if i["id"] == "login")
    assert login_item["ok"] is True


def test_launch_check_forbidden_for_influencer(infl_tok):
    r = requests.get(f"{BASE}/api/admin/launch-check", headers={"Authorization": f"Bearer {infl_tok}"}, timeout=15)
    assert r.status_code == 403


# --- Poster PDF ---
def _dashboard_campaign_id(tok, path):
    r = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"
    d = r.json()
    # find campaigns list
    for k in ("campaigns", "campanhas"):
        if k in d and d[k]:
            return d[k][0]["id"]
    # fallback
    return None


def test_poster_pdf_influencer(infl_tok):
    dash = requests.get(f"{BASE}/api/dashboard/influencer", headers={"Authorization": f"Bearer {infl_tok}"}, timeout=15).json()
    cid = None
    for k, v in dash.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "cupom" in v[0]:
            cid = v[0]["id"]; break
    assert cid, f"no campaign id in dash keys={list(dash.keys())}"
    r = requests.get(f"{BASE}/api/campaigns/{cid}/poster.pdf", headers={"Authorization": f"Bearer {infl_tok}"}, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 5000, f"pdf too small: {len(r.content)}"
    assert r.content.startswith(b"%PDF")


def test_poster_pdf_partner(part_tok, admin_tok):
    dash = requests.get(f"{BASE}/api/dashboard/partner", headers={"Authorization": f"Bearer {part_tok}"}, timeout=15).json()
    pid = dash["partner"]["id"]
    # find campaign belonging to this partner via admin campanhas
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers={"Authorization": f"Bearer {admin_tok}"}, timeout=10).json()
    cid = next((c["id"] for c in camps if c.get("parceiro_id") == pid), None)
    assert cid, f"no campaign for partner {pid}"
    r = requests.get(f"{BASE}/api/campaigns/{cid}/poster.pdf", headers={"Authorization": f"Bearer {part_tok}"}, timeout=30)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 5000


def test_poster_pdf_404(infl_tok):
    r = requests.get(f"{BASE}/api/campaigns/nope-xxx/poster.pdf", headers={"Authorization": f"Bearer {infl_tok}"}, timeout=15)
    assert r.status_code == 404


# --- PWA assets ---
def test_manifest_short_name():
    r = requests.get(f"{BASE}/manifest.json", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j.get("short_name") == "RRclub", f"got {j.get('short_name')!r}"


def test_icon_192():
    r = requests.get(f"{BASE}/icon-192.png", timeout=15)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 500
