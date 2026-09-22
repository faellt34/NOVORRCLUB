"""Iteration 16 - Config bug fixes: launch-check email/coupon/domain + frontend_url."""
import os
import re
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "faellt@gmail.com"
ADMIN_PASSWORD = "Robson2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


def test_launch_check_email_coupon_domain(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/launch-check", headers=admin_headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("checks") or data
    # Normalize items list
    if isinstance(items, dict):
        items = items.get("items", [])
    print("LAUNCH-CHECK items:", items)

    by_id = {it.get("id"): it for it in items if isinstance(it, dict)}

    assert "email" in by_id, f"email item missing. keys={list(by_id.keys())}"
    email_item = by_id["email"]
    assert email_item.get("ok") is True, f"email item not ok: {email_item}"

    assert "coupon_public" in by_id, f"coupon_public missing. keys={list(by_id.keys())}"
    coupon = by_id["coupon_public"]
    assert coupon.get("hint") == "https://rrclub.online/c/CLUB-10", f"coupon hint={coupon.get('hint')}"

    assert "domain" in by_id, f"domain missing. keys={list(by_id.keys())}"
    domain = by_id["domain"]
    label = (domain.get("label") or "") + " " + (domain.get("hint") or "")
    assert "rrclub.online" in label, f"domain label/hint missing rrclub.online: {domain}"


def test_admin_settings_email_configured(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/settings", headers=admin_headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    print("SETTINGS keys:", list(data.keys()))
    assert data.get("email_configured") is True, f"email_configured={data.get('email_configured')}"
    sender = data.get("sender_email")
    assert isinstance(sender, str) and len(sender) > 0, f"sender_email invalid: {sender!r}"


def test_public_site_frontend_url():
    r = requests.get(f"{BASE_URL}/api/public/site", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    print("PUBLIC/SITE:", data)
    assert data.get("frontend_url") == "https://rrclub.online", f"frontend_url={data.get('frontend_url')}"


def test_no_theclub_references_in_repo():
    paths = ["/app/backend", "/app/frontend/src", "/app/frontend/public"]
    hits = []
    for p in paths:
        if not os.path.exists(p):
            continue
        # exclude node_modules, __pycache__
        cmd = ["grep", "-ril", "--exclude-dir=node_modules", "--exclude-dir=__pycache__",
               "--exclude-dir=.git", "--exclude-dir=tests", "--exclude-dir=.pytest_cache", "theclub", p]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout.strip():
            hits.extend(res.stdout.strip().split("\n"))
    # also check .env
    env_path = "/app/backend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            content = f.read()
        if re.search(r"theclub", content, re.IGNORECASE):
            hits.append(env_path)
    assert not hits, f"Found 'theclub' references in: {hits}"


def test_email_test_endpoint(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/settings/email/test", headers=admin_headers, timeout=30)
    print(f"EMAIL TEST status={r.status_code} body={r.text[:400]}")
    # 200 or 502 both acceptable
    assert r.status_code in (200, 502), f"Unexpected status {r.status_code}: {r.text}"
