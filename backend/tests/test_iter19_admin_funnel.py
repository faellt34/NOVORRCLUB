"""Iter 19 - Admin dashboard funnel + origins card + live updates from clique_cupao/split_executado."""
import os
import time
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "faellt@gmail.com", "password": "Robson2026!"}
PARTNER = {"email": "parceiro.exemplo@club.pt", "password": "parceiro123"}


def _login(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def partner_headers():
    return {"Authorization": f"Bearer {_login(PARTNER)}"}


def test_admin_dashboard_funnel_shape(admin_headers):
    r = requests.get(f"{BASE}/api/dashboard/admin", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "funnel" in d and "trend" in d and "totals" in d
    f = d["funnel"]
    for k in ["clicks", "uses", "not_used", "conversion", "ticket", "origins"]:
        assert k in f, f"missing funnel.{k}"
    assert f["not_used"] == max(f["clicks"] - f["uses"], 0)
    expected_conv = round(f["uses"] / f["clicks"] * 100, 1) if f["clicks"] else 0
    assert f["conversion"] == expected_conv
    assert isinstance(f["origins"], list)
    for o in f["origins"]:
        assert "origem" in o and "clicks" in o
    assert "count" in d["trend"]


def test_click_increases_funnel_and_origin_instagram(admin_headers):
    r0 = requests.get(f"{BASE}/api/dashboard/admin", headers=admin_headers, timeout=30).json()["funnel"]
    ua = f"Instagram/{uuid.uuid4().hex} Mozilla/5.0 (iPhone) InstagramApp"
    rc = requests.get(f"{BASE}/api/public/coupon/CLUB-10?src=instagram",
                     headers={"User-Agent": ua}, timeout=30)
    assert rc.status_code == 200, rc.text
    time.sleep(1.5)
    r1 = requests.get(f"{BASE}/api/dashboard/admin", headers=admin_headers, timeout=30).json()["funnel"]
    assert r1["clicks"] == r0["clicks"] + 1, f"clicks {r0['clicks']}->{r1['clicks']}"
    assert r1["not_used"] == r0["not_used"] + 1
    ig = next((o for o in r1["origins"] if o["origem"].lower() == "instagram"), None)
    assert ig is not None, f"instagram origem missing: {r1['origins']}"
    ig0 = next((o for o in r0["origins"] if o["origem"].lower() == "instagram"), {"clicks": 0})
    assert ig["clicks"] == ig0["clicks"] + 1


def test_redemption_updates_uses_conversion_ticket(admin_headers, partner_headers):
    r0 = requests.get(f"{BASE}/api/dashboard/admin", headers=admin_headers, timeout=30).json()
    f0 = r0["funnel"]
    rev0 = r0["totals"]["revenue"]
    body = {"code": "CLUB-10", "amount": 40, "paid_online": False, "idempotency_key": f"iter19-{uuid.uuid4().hex}"}
    rp = requests.post(f"{BASE}/api/redemptions", json=body, headers=partner_headers, timeout=30)
    assert rp.status_code in (200, 201), rp.text
    rid = rp.json().get("id")
    print(f"CREATED_REDEMPTION_ID={rid}")
    time.sleep(1.5)
    r1 = requests.get(f"{BASE}/api/dashboard/admin", headers=admin_headers, timeout=30).json()
    f1 = r1["funnel"]
    assert f1["uses"] == f0["uses"] + 1
    if f1["clicks"]:
        assert f1["conversion"] == round(f1["uses"] / f1["clicks"] * 100, 1)
    # revenue increases by valor_plataforma (10% of amount typical)
    assert r1["totals"]["revenue"] >= rev0  # non-decreasing; exact delta depends on commission
    # ticket == totals.revenue / uses rounded
    assert abs(f1["ticket"] - round(r1["totals"]["revenue"] / f1["uses"], 2)) < 0.01 if f1["uses"] else True
