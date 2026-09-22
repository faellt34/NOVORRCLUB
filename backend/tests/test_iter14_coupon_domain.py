"""Iter14: Coupon links/QR/poster must use backend FRONTEND_URL (rrclub.online), not preview or 'theclub'."""
import io
import os
import re
import pytest
import requests
from pypdf import PdfReader


def _pdf_text(body: bytes) -> str:
    reader = PdfReader(io.BytesIO(body))
    return "\n".join((p.extract_text() or "") for p in reader.pages)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

EXPECTED_SITE = "https://rrclub.online"
EXPECTED_COUPON = "https://rrclub.online/c/CLUB-10"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def influencer_token():
    return _login("influencer.exemplo@club.pt", "influencer123")


@pytest.fixture(scope="module")
def admin_token():
    return _login("faellt@gmail.com", "Robson2026!")


# ---- GET /api/public/site ----
def test_public_site_returns_rrclub():
    r = requests.get(f"{API}/public/site", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("frontend_url") == EXPECTED_SITE, data


# ---- Poster PDF uses FRONTEND_URL and ignores ?site= ----
def _get_influencer_campaign_id(token):
    r = requests.get(f"{API}/dashboard/influencer", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    assert r.status_code == 200, r.text
    camps = r.json().get("campaigns", [])
    club10 = [c for c in camps if c.get("cupom") == "CLUB-10"]
    assert club10, f"CLUB-10 not found: {camps}"
    return club10[0]["id"]


def test_poster_pdf_contains_rrclub_link(influencer_token):
    cid = _get_influencer_campaign_id(influencer_token)
    r = requests.get(
        f"{API}/campaigns/{cid}/poster.pdf",
        headers={"Authorization": f"Bearer {influencer_token}"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    text = _pdf_text(r.content)
    assert "rrclub.online/c/CLUB-10" in text, f"Expected rrclub.online/c/CLUB-10 in poster PDF, got: {text[:500]}"
    assert "theclub" not in text.lower(), "'theclub' leaked into poster PDF"


def test_poster_pdf_ignores_site_query(influencer_token):
    cid = _get_influencer_campaign_id(influencer_token)
    r = requests.get(
        f"{API}/campaigns/{cid}/poster.pdf?site=https://evil.example",
        headers={"Authorization": f"Bearer {influencer_token}"},
        timeout=60,
    )
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "evil" not in text.lower(), "'evil' from ?site= leaked into poster PDF"
    assert "rrclub.online/c/CLUB-10" in text


# ---- Story video ----
def test_story_video_returns_mp4(influencer_token):
    cid = _get_influencer_campaign_id(influencer_token)
    r = requests.get(
        f"{API}/influencer/story-video/{cid}",
        headers={"Authorization": f"Bearer {influencer_token}"},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "mp4" in ct or "video" in ct, f"unexpected ct: {ct}"
    assert len(r.content) > 1000


# ---- Admin launch check ----
def test_launch_check_mentions_rrclub(admin_token):
    r = requests.get(
        f"{API}/admin/launch-check",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("frontend_url") == EXPECTED_SITE, data
    items = data.get("items", [])
    domain = next((i for i in items if i.get("id") == "domain"), None)
    assert domain, f"no domain item: {items}"
    assert "rrclub.online" in domain.get("label", ""), domain
    coupon = next((i for i in items if i.get("id") == "coupon_public"), None)
    if coupon:
        # hint should contain the rrclub coupon URL
        assert EXPECTED_COUPON in (coupon.get("hint", "") + coupon.get("label", "")), coupon
