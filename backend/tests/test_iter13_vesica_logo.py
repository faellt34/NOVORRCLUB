"""Iter 13 — Vesica Piscis logo regression: PWA icons, manifest, poster PDF, story video."""
import os
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE:
    # fallback to reading frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
                break

INFLU = {"email": "influencer.exemplo@club.pt", "password": "influencer123"}


def _login(cred):
    r = requests.post(f"{BASE}/api/auth/login", json=cred, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_icon_192_png():
    r = requests.get(f"{BASE}/icon-192.png", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/png"), r.headers
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(r.content) > 500


def test_icon_512_png():
    r = requests.get(f"{BASE}/icon-512.png", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(r.content) > 1000


def test_manifest_theme_color():
    r = requests.get(f"{BASE}/manifest.json", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("theme_color", "").lower() == "#6e2bff", data


def _pick_campaign(token):
    # try influencer dashboard for a campaign id
    r = requests.get(f"{BASE}/api/dashboard/influencer", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    # Try common shapes
    for key in ("campaigns", "active_campaigns"):
        if isinstance(data.get(key), list) and data[key]:
            c = data[key][0]
            return c.get("id") or c.get("_id") or c.get("campaign_id") or c.get("cupom") or "CLUB-10"
    # fallback
    return "CLUB-10"


def test_poster_pdf_valid_over_5kb():
    token = _login(INFLU)
    cid = _pick_campaign(token)
    r = requests.get(f"{BASE}/api/campaigns/{cid}/poster.pdf",
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    assert r.content[:4] == b"%PDF", r.content[:20]
    assert len(r.content) > 5 * 1024, f"pdf size {len(r.content)}"


def test_story_video_mp4():
    token = _login(INFLU)
    cid = _pick_campaign(token)
    r = requests.get(f"{BASE}/api/influencer/story-video/{cid}",
                     headers={"Authorization": f"Bearer {token}"}, timeout=90)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    ct = r.headers.get("content-type", "")
    assert "video/mp4" in ct or "mp4" in ct, ct
    assert len(r.content) > 10 * 1024, f"video size {len(r.content)}"
