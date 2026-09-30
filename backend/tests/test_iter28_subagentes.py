"""Iter 28 — Diretor IA subagentes (marketing, frontend, backend). Each call may take 20-60s."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:3000").rstrip("/") \
    if os.environ.get("REACT_APP_BACKEND_URL") else None

# Fallback: read from frontend .env
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

TIMEOUT = 180


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "faellt@gmail.com", "password": "Robson2026!"},
                      timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def _conversar(headers, mensagem, expected_func):
    """Call POST /api/diretor/conversar; retry once with explicit invocation if the subagent isn't chosen."""
    for attempt in range(2):
        msg = mensagem if attempt == 0 else f"Chama a função {expected_func} diretamente. {mensagem}"
        r = requests.post(f"{BASE_URL}/api/diretor/conversar",
                          json={"mensagem": msg}, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("resposta_diretor"), "resposta_diretor should be non-empty"
        funcs = [c["funcao"] for c in body.get("chamadas", [])]
        if expected_func in funcs:
            return body
    pytest.fail(f"Subagent {expected_func} not called after retry. Funcs seen: {funcs}")


# --- Subagente Marketing ---
def test_subagente_marketing(headers):
    body = _conversar(headers,
                      "Pede ao subagente Marketing um plano em 3 pontos para aumentar a conversão",
                      "subagente_marketing")
    ch = next(c for c in body["chamadas"] if c["funcao"] == "subagente_marketing")
    assert ch["resumo"], "resumo (analise) must be non-empty for subagente_marketing"
    assert len(ch["resumo"]) > 20


# --- Subagente Frontend ---
def test_subagente_frontend_publiccoupon(headers):
    body = _conversar(headers,
                      "Pede ao subagente Frontend para auditar o ficheiro PublicCoupon.jsx",
                      "subagente_frontend")
    ch = next(c for c in body["chamadas"] if c["funcao"] == "subagente_frontend")
    assert ch["resumo"] and len(ch["resumo"]) > 20


# --- Subagente Backend + segurança (nenhum segredo revelado) ---
SECRET_PATTERN = re.compile(r"\b(sk_(live|test)_[A-Za-z0-9]{6,}|re_[A-Za-z0-9]{8,}|whsec_[A-Za-z0-9]{6,})\b")


def test_subagente_backend_no_secret_leak(headers):
    body = _conversar(headers,
                      "Pede ao subagente Backend uma revisão de segurança de routes_payments.py em 3 pontos",
                      "subagente_backend")
    ch = next(c for c in body["chamadas"] if c["funcao"] == "subagente_backend")
    assert ch["resumo"] and len(ch["resumo"]) > 20
    combined = (ch["resumo"] + "\n" + body["resposta_diretor"])
    m = SECRET_PATTERN.search(combined)
    assert not m, f"Secret-like token leaked in output: {m.group(0) if m else ''}"
