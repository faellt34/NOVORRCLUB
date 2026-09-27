"""Iter 10 — Influencer AI captions endpoint."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0].strip()
BASE_URL = BASE_URL.rstrip("/")
UA = {"User-Agent": "Mozilla/5.0 test", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, headers=UA, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def influencer_token():
    return _login("influencer.exemplo@club.pt", "influencer123")


@pytest.fixture(scope="module")
def partner_token():
    return _login("parceiro.exemplo@club.pt", "parceiro123")


@pytest.fixture(scope="module")
def admin_token():
    return _login("faellt@gmail.com", "Robson2026!")


@pytest.fixture(scope="module")
def influencer_campaign_id(influencer_token):
    r = requests.get(f"{BASE_URL}/api/dashboard/influencer", headers={**UA, "Authorization": f"Bearer {influencer_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    campaigns = r.json().get("campaigns", [])
    assert campaigns, "no campaigns for influencer"
    return campaigns[0]["id"], campaigns[0]["cupom"]


def test_captions_ok(influencer_token, influencer_campaign_id):
    cid, cupom = influencer_campaign_id
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/captions",
        json={"campaign_id": cid, "tom": "divertido"},
        headers={**UA, "Authorization": f"Bearer {influencer_token}"},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cupom"] == cupom
    assert f"/c/{cupom}" in d["link"]
    caps = d["captions"]
    for lang in ("pt", "en", "es"):
        assert isinstance(caps.get(lang), list) and len(caps[lang]) >= 1, f"lang {lang} empty: {caps}"
        assert any(cupom in s for s in caps[lang]), f"cupom {cupom} not in any {lang} caption: {caps[lang]}"


def test_captions_invalid_campaign(influencer_token):
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/captions",
        json={"campaign_id": "cmp_does_not_exist", "tom": "elegante"},
        headers={**UA, "Authorization": f"Bearer {influencer_token}"},
        timeout=30,
    )
    assert r.status_code == 404, r.text


def test_captions_forbidden_partner(partner_token, influencer_campaign_id):
    cid, _ = influencer_campaign_id
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/captions",
        json={"campaign_id": cid, "tom": "elegante"},
        headers={**UA, "Authorization": f"Bearer {partner_token}"},
        timeout=30,
    )
    assert r.status_code == 403, r.text


def test_captions_forbidden_admin(admin_token, influencer_campaign_id):
    cid, _ = influencer_campaign_id
    r = requests.post(
        f"{BASE_URL}/api/influencer/ai/captions",
        json={"campaign_id": cid, "tom": "elegante"},
        headers={**UA, "Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert r.status_code == 403, r.text
