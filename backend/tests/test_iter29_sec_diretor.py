"""Iter 29 — security fixes in routes_payments + Diretor propor_correcao"""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if "REACT_APP_BACKEND_URL" in os.environ else "https://robson-dashboard.preview.emergentagent.com"
UA = {"User-Agent": "Mozilla/5.0 (iter29-tester)"}

ADMIN = ("faellt@gmail.com", "Robson2026!")
INF = ("influencer.exemplo@club.pt", "influencer123")
PART = ("parceiro.exemplo@club.pt", "parceiro123")


def _login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, headers=UA, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def tokens():
    return {"admin": _login(*ADMIN), "inf": _login(*INF), "part": _login(*PART)}


def _h(tok):
    return {**UA, "Authorization": f"Bearer {tok}"}


# ----- payments/status -----
def test_payments_status_authz(tokens):
    # find a premium ebook lookup_key
    ebs = requests.get(f"{BASE}/api/ebooks", headers=_h(tokens["inf"]), timeout=30).json()
    premium = next((e for e in ebs if e.get("premium") and e.get("preco")), None)
    if not premium:
        pytest.skip("no premium ebook available")
    lookup_key = f"ebook_{premium['id']}"
    r = requests.post(f"{BASE}/api/payments/checkout",
                      json={"lookup_key": lookup_key, "origin_url": "https://example.com"},
                      headers=_h(tokens["inf"]), timeout=60)
    if r.status_code == 409:
        # already owns — try monthly subscription instead
        r = requests.post(f"{BASE}/api/payments/checkout",
                          json={"lookup_key": "club_monthly", "origin_url": "https://example.com"},
                          headers=_h(tokens["inf"]), timeout=60)
    assert r.status_code == 200, f"checkout: {r.status_code} {r.text[:300]}"
    sid = r.json()["session_id"]
    print(f"created session {sid}")

    # no token -> 401
    r0 = requests.get(f"{BASE}/api/payments/status/{sid}", headers=UA, timeout=30)
    assert r0.status_code == 401, f"no-token expected 401, got {r0.status_code}"

    # admin -> 200
    r1 = requests.get(f"{BASE}/api/payments/status/{sid}", headers=_h(tokens["admin"]), timeout=30)
    assert r1.status_code == 200, f"admin expected 200, got {r1.status_code} {r1.text[:200]}"

    # owner (inf) -> 200
    r2 = requests.get(f"{BASE}/api/payments/status/{sid}", headers=_h(tokens["inf"]), timeout=30)
    assert r2.status_code == 200, f"owner expected 200, got {r2.status_code}"

    # partner (other) -> 403
    r3 = requests.get(f"{BASE}/api/payments/status/{sid}", headers=_h(tokens["part"]), timeout=30)
    assert r3.status_code == 403, f"other user expected 403, got {r3.status_code}"


def test_payments_status_not_found():
    r = requests.get(f"{BASE}/api/payments/status/cs_test_fake_nonexistent", headers=UA, timeout=30)
    assert r.status_code == 404


# ----- webhook -----
def test_stripe_webhook_bad_sig():
    r = requests.post(f"{BASE}/api/stripe/webhook", data="{}", headers={**UA, "Content-Type": "application/json"}, timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"


# ----- pdf -----
def test_pdf_no_query_auth(tokens):
    ebs = requests.get(f"{BASE}/api/ebooks", headers=_h(tokens["inf"]), timeout=30).json()
    if not ebs:
        pytest.skip("no ebooks")
    eid = ebs[0]["id"]
    # ?auth=... with NO Authorization header -> 401
    r0 = requests.get(f"{BASE}/api/ebooks/{eid}/pdf?auth={tokens['inf']}", headers=UA, timeout=30)
    assert r0.status_code == 401, f"query auth should be rejected, got {r0.status_code}"

    # header -> not 401
    r1 = requests.get(f"{BASE}/api/ebooks/{eid}/pdf", headers=_h(tokens["inf"]), timeout=30)
    assert r1.status_code in (200, 403, 404), f"got {r1.status_code}"


# ----- Diretor propor_correcao -----
def test_diretor_propor_correcao(tokens):
    msg = ("Chama a função propor_correcao com area backend, ficheiro routes_payments.py, "
           "descricao \"Validar content_type do PDF\" e diff "
           "\"--- a/routes_payments.py\\n+++ b/routes_payments.py\\n@@\\n+    if file.content_type != \\\"application/pdf\\\": raise HTTPException(400)\"")
    r = requests.post(f"{BASE}/api/diretor/conversar", json={"mensagem": msg}, headers=_h(tokens["admin"]), timeout=200)
    assert r.status_code == 200, f"conversar: {r.status_code} {r.text[:300]}"
    data = r.json()
    pend = data.get("acoes_pendentes") or []
    pc = next((a for a in pend if a.get("tipo_acao") == "propor_correcao"), None)
    assert pc, f"no propor_correcao pending action; got: {[a.get('tipo_acao') for a in pend]}; resposta={data.get('resposta_diretor','')[:200]}"
    acao_id = pc["id"]
    print(f"pending propor_correcao {acao_id}")

    # approve
    ap = requests.post(f"{BASE}/api/diretor/acoes/{acao_id}/aprovar", headers=_h(tokens["admin"]), timeout=60)
    assert ap.status_code == 200
    res = ap.json().get("resultado", {})
    pf = res.get("patch_file", "")
    assert pf.startswith("memory/patches/"), f"unexpected patch_file: {pf}"
    disk = os.path.join("/app", pf)
    assert os.path.isfile(disk), f"patch file missing on disk: {disk}"
    print(f"patch persisted at {disk}")

    # listing approved includes it
    li = requests.get(f"{BASE}/api/diretor/acoes?status=aprovada", headers=_h(tokens["admin"]), timeout=30)
    assert li.status_code == 200
    ids = [a["id"] for a in li.json()]
    assert acao_id in ids

    # cleanup
    try:
        os.remove(disk)
    except Exception:
        pass
