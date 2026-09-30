"""Iter 26 — Influencer AI Story Image (Gemini Nano Banana) endpoint tests."""
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")
INF = ("influencer.exemplo@club.pt", "influencer123")
PART = ("parceiro.exemplo@club.pt", "parceiro123")
ADMIN = ("faellt@gmail.com", "Robson2026!")


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def inf_token():
    return _login(*INF)


@pytest.fixture(scope="module")
def partner_token():
    return _login(*PART)


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def campaign_id(inf_token):
    r = requests.get(f"{BASE_URL}/api/dashboard/influencer",
                     headers={"Authorization": f"Bearer {inf_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    camps = r.json().get("campaigns") or []
    assert camps, "no campaigns for influencer"
    return camps[0]["id"]


def test_story_image_success_noite(inf_token, campaign_id):
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/story-image",
        json={"campaign_id": campaign_id, "estilo": "noite"},
        headers={"Authorization": f"Bearer {inf_token}"},
        timeout=120,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    ct = r.headers.get("content-type", "")
    assert ct.startswith("image/"), f"content-type={ct}"
    assert len(r.content) > 50_000, f"body too small: {len(r.content)}"
    img = Image.open(io.BytesIO(r.content))
    assert img.height > img.width, f"not portrait: {img.size}"
    print(f"OK image {img.size} bytes={len(r.content)} ct={ct}")


def test_story_image_invalid_campaign(inf_token):
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/story-image",
        json={"campaign_id": "nope-xyz", "estilo": "luxo"},
        headers={"Authorization": f"Bearer {inf_token}"},
        timeout=30,
    )
    assert r.status_code == 404, f"{r.status_code} {r.text}"


def test_story_image_partner_forbidden(partner_token, campaign_id):
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/story-image",
        json={"campaign_id": campaign_id, "estilo": "luxo"},
        headers={"Authorization": f"Bearer {partner_token}"},
        timeout=30,
    )
    assert r.status_code == 403, f"{r.status_code} {r.text}"


def test_story_image_admin_forbidden(admin_token, campaign_id):
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/story-image",
        json={"campaign_id": campaign_id, "estilo": "luxo"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 403, f"{r.status_code} {r.text}"
