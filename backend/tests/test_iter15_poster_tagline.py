"""Iter15: poster.pdf must show RRCLUB.ONLINE tagline (no theclub) for influencer and partner."""
import io
import os
import re
import requests
import pytest
import fitz  # pymupdf

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://robson-dashboard.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _pdf_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _get_campaign_id(token):
    r = requests.get(f"{BASE_URL}/api/dashboard/influencer", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    assert r.status_code == 200, f"dashboard failed: {r.status_code} {r.text}"
    data = r.json()
    # Try multiple shapes
    for key in ("campaigns", "campanhas"):
        if key in data and data[key]:
            c = data[key][0]
            return c.get("id") or c.get("_id") or c.get("campaign_id")
    # fallback: search recursively
    def find_id(obj):
        if isinstance(obj, dict):
            if "id" in obj and "cupom" in obj:
                return obj["id"]
            for v in obj.values():
                r = find_id(v)
                if r:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = find_id(v)
                if r:
                    return r
        return None
    cid = find_id(data)
    assert cid, f"no campaign id found in dashboard: {data}"
    return cid


def _assert_poster(pdf_bytes):
    text = _pdf_text(pdf_bytes)
    assert "theclub" not in text.lower(), f"'theclub' still present in poster PDF text: {text[:500]}"
    assert "RRCLUB.ONLINE" in text.upper(), f"'RRCLUB.ONLINE' tagline missing: {text[:500]}"
    assert "rrclub.online/c/CLUB-10" in text, f"coupon link rrclub.online/c/CLUB-10 missing: {text[:500]}"


def test_poster_influencer():
    token = _login("influencer.exemplo@club.pt", "influencer123")
    cid = _get_campaign_id(token)
    r = requests.get(f"{BASE_URL}/api/campaigns/{cid}/poster.pdf",
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    assert r.status_code == 200, f"poster.pdf failed: {r.status_code} {r.text[:300]}"
    assert r.content[:4] == b"%PDF", "response is not a PDF"
    _assert_poster(r.content)


def test_poster_partner():
    # partner login
    token = _login("parceiro.exemplo@club.pt", "parceiro123")
    # get a campaign id from partner dashboard
    r = requests.get(f"{BASE_URL}/api/dashboard/parceiro", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code != 200:
        # try alt endpoint
        r = requests.get(f"{BASE_URL}/api/dashboard/partner", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    assert r.status_code == 200, f"partner dashboard failed: {r.status_code} {r.text[:300]}"
    data = r.json()

    def find_id(obj):
        if isinstance(obj, dict):
            if "id" in obj and ("cupom" in obj or "codigo" in obj):
                return obj["id"]
            for v in obj.values():
                res = find_id(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for v in obj:
                res = find_id(v)
                if res:
                    return res
        return None
    cid = find_id(data)
    assert cid, f"no campaign id in partner dashboard: {data}"

    r = requests.get(f"{BASE_URL}/api/campaigns/{cid}/poster.pdf",
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    assert r.status_code == 200, f"partner poster.pdf failed: {r.status_code} {r.text[:300]}"
    assert r.content[:4] == b"%PDF"
    _assert_poster(r.content)


def test_repo_no_theclub():
    """Sanity: no case-insensitive 'theclub' in backend py or frontend src."""
    import subprocess, glob
    backend_files = glob.glob("/app/backend/*.py")
    result = subprocess.run(
        ["grep", "-ri", "-l", "theclub", *backend_files, "/app/frontend/src/"],
        capture_output=True, text=True
    )
    # grep returns 1 when no matches
    assert result.returncode == 1, f"'theclub' still present in: {result.stdout}"
