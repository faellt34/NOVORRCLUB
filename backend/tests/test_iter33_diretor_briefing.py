"""Iter 33 — Diretor proativo: /briefing, /logs, /metricas, auth, /conversar com logs"""
import os
import time
import pytest
import requests

def _load_base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            for line in open("/app/frontend/.env"):
                if line.startswith("REACT_APP_BACKEND_URL="):
                    v = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")


BASE = _load_base()
ADMIN = {"email": "faellt@gmail.com", "password": "Robson2026!"}
INFL = {"email": "influencer.exemplo@club.pt", "password": "influencer123"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def infl_token():
    r = requests.post(f"{BASE}/api/auth/login", json=INFL, timeout=20)
    if r.status_code != 200:
        pytest.skip("influencer login failed")
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


# --- /briefing ---
def test_briefing_shape(admin_token):
    r = requests.get(f"{BASE}/api/diretor/briefing", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    b = r.json()
    assert set(["alertas", "saude", "top_campanhas", "funil_30d"]).issubset(b.keys())
    s = b["saude"]
    for k in ("pedidos_api", "erros_500", "pedidos_lentos_1500ms", "rotas_mais_lentas"):
        assert k in s, f"saude.{k} em falta"
    assert isinstance(b["alertas"], list)
    f = b["funil_30d"]
    for k in ("cliques", "qr_baixados", "vendas", "receita"):
        assert k in f


# --- /logs with 404 appearing as warn ---
def test_logs_contain_404_warning(admin_token):
    # Generate a 404
    requests.get(f"{BASE}/api/rota-inexistente-xyz-33", timeout=10)
    time.sleep(1.5)  # middleware persists async
    r = requests.get(f"{BASE}/api/diretor/logs?nivel=warn&horas=24", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    for k in ("totais", "rotas_mais_afetadas", "logs", "auditoria_recente"):
        assert k in data
    paths = [l.get("caminho", "") for l in data["logs"]]
    assert any("rota-inexistente-xyz-33" in p for p in paths), f"404 não apareceu nos logs warn: {paths[:5]}"


# --- /metricas dimensoes ---
@pytest.mark.parametrize("dim", ["campanha", "influencer", "hotel"])
def test_metricas_dimensao(admin_token, dim):
    r = requests.get(f"{BASE}/api/diretor/metricas?dimensao={dim}&dias=30", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("dimensao") == dim
    assert "itens" in d and isinstance(d["itens"], list)
    if d["itens"]:
        it = d["itens"][0]
        for k in ("cliques", "qr_baixados", "vendas", "receita", "taxa_qr_pct", "conversao_pct", "ticket_medio", "alerta"):
            assert k in it, f"campo {k} em falta no item {dim}"


def test_metricas_qr(admin_token):
    r = requests.get(f"{BASE}/api/diretor/metricas?dimensao=qr&dias=30", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("dimensao") == "qr"
    for k in ("funil", "por_origem", "por_dia"):
        assert k in d


def test_metricas_invalida(admin_token):
    r = requests.get(f"{BASE}/api/diretor/metricas?dimensao=xpto", headers=H(admin_token), timeout=30)
    assert r.status_code == 200
    assert "erro" in r.json()


# --- auth: /diretor exige admin ---
def test_diretor_no_token():
    r = requests.get(f"{BASE}/api/diretor/briefing", timeout=15)
    assert r.status_code in (401, 403)


def test_diretor_influencer_forbidden(infl_token):
    r = requests.get(f"{BASE}/api/diretor/briefing", headers=H(infl_token), timeout=15)
    assert r.status_code == 403


# --- /conversar should call consultar_logs / diagnosticar_sistema (max 1 LLM call) ---
def test_conversar_logs_calls(admin_token):
    r = requests.post(f"{BASE}/api/diretor/conversar",
                      headers=H(admin_token),
                      json={"mensagem": "Há erros nos logs das últimas 24h?"},
                      timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "chamadas" in data
    funcs = [c.get("funcao") for c in data["chamadas"]]
    assert any(f in ("consultar_logs", "diagnosticar_sistema") for f in funcs), f"funções chamadas: {funcs}"
