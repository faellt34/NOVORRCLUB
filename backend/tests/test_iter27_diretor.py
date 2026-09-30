"""Iter 27 — Diretor IA (Gemini 2.5 Flash) backend tests."""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
UA = {"User-Agent": "Mozilla/5.0 rrclub-test"}
ADMIN = ("faellt@gmail.com", "Robson2026!")
PARTNER = ("parceiro.exemplo@club.pt", "parceiro123")


def _login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, headers=UA, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(*ADMIN)}", **UA}


@pytest.fixture(scope="module")
def partner_h():
    return {"Authorization": f"Bearer {_login(*PARTNER)}", **UA}


@pytest.fixture(scope="module")
def ids(admin_h):
    p = requests.get(f"{BASE}/api/admin/parceiros", headers=admin_h, timeout=30).json()
    i = requests.get(f"{BASE}/api/admin/influencers", headers=admin_h, timeout=30).json()
    parc = next((x for x in p if "Exemplo" in (x.get("nome") or "")), p[0])
    infl = next((x for x in i if "Exemplo" in (x.get("nome") or "")), i[0])
    return {"hotel_id": parc["id"], "influencer_id": infl["id"], "hotel_nome": parc["nome"], "influencer_nome": infl["nome"]}


def _conversar(h, msg):
    r = requests.post(f"{BASE}/api/diretor/conversar", json={"mensagem": msg}, headers=h, timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def test_01_forbidden_for_partner(partner_h):
    r = requests.post(f"{BASE}/api/diretor/conversar", json={"mensagem": "oi"}, headers=partner_h, timeout=30)
    assert r.status_code == 403


def test_02_conversar_dashboard(admin_h):
    d = _conversar(admin_h, "Faz um resumo do dashboard com receita e vendas dos últimos 30 dias.")
    assert d["resposta_diretor"].strip()
    fns = [c["funcao"] for c in d.get("chamadas", [])]
    assert "ler_dashboard" in fns, f"chamadas={fns}"


def test_03_criar_campanha_pendente_e_aprovar(admin_h, ids):
    msg = (f"Cria uma campanha QR chamada 'Teste Diretor' para o hotel id {ids['hotel_id']} "
           f"({ids['hotel_nome']}) com o influencer id {ids['influencer_id']} ({ids['influencer_nome']}), "
           f"de 2026-11-01 a 2026-11-30. Chama diretamente criar_campanha com esses ids.")
    d = _conversar(admin_h, msg)
    pend = [a for a in d.get("acoes_pendentes", []) if a["tipo_acao"] == "criar_campanha"]
    if not pend:
        # retry once with even more explicit prompt
        d = _conversar(admin_h, msg + " NÃO respondas em texto, chama criar_campanha agora.")
        pend = [a for a in d.get("acoes_pendentes", []) if a["tipo_acao"] == "criar_campanha"]
    assert pend, f"no criar_campanha queued. resp={d.get('resposta_diretor')}"
    acao = pend[0]
    assert acao["status"] == "pendente"
    acao_id = acao["id"]

    # GET /acoes?status=pendente lists it
    lst = requests.get(f"{BASE}/api/diretor/acoes?status=pendente", headers=admin_h, timeout=30).json()
    assert any(a["id"] == acao_id for a in lst)

    # Approve
    r = requests.post(f"{BASE}/api/diretor/acoes/{acao_id}/aprovar", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["resultado"].get("cupom")
    cupom = body["resultado"]["cupom"]

    # Second approve -> 404
    r2 = requests.post(f"{BASE}/api/diretor/acoes/{acao_id}/aprovar", headers=admin_h, timeout=30)
    assert r2.status_code == 404

    # Campaign visible in admin list
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers=admin_h, timeout=30).json()
    match = [c for c in camps if c.get("cupom") == cupom]
    assert match, f"campanha com cupom {cupom} não encontrada"
    pytest.created_campaign_ids = getattr(pytest, "created_campaign_ids", []) + [match[0]["id"]]


def test_04_gerar_contrato_pendente_rejeitar(admin_h, ids):
    msg = (f"Gera um contrato entre o hotel id {ids['hotel_id']} e o influencer id {ids['influencer_id']} "
           f"com split hotel 75 influencer 5 rrclub 10 stripe 10, duração 90 dias. Chama gerar_contrato.")
    d = _conversar(admin_h, msg)
    pend = [a for a in d.get("acoes_pendentes", []) if a["tipo_acao"] == "gerar_contrato"]
    if not pend:
        d = _conversar(admin_h, msg + " Chama gerar_contrato agora, sem texto adicional.")
        pend = [a for a in d.get("acoes_pendentes", []) if a["tipo_acao"] == "gerar_contrato"]
    assert pend, f"gerar_contrato não pendente. resp={d.get('resposta_diretor')}"
    aid = pend[0]["id"]

    r = requests.post(f"{BASE}/api/diretor/acoes/{aid}/rejeitar", headers=admin_h, timeout=30)
    assert r.status_code == 200 and r.json()["ok"]

    lst = requests.get(f"{BASE}/api/diretor/acoes?status=rejeitada", headers=admin_h, timeout=30).json()
    assert any(a["id"] == aid for a in lst)


def test_05_conversas_history(admin_h):
    r = requests.get(f"{BASE}/api/diretor/conversas", headers=admin_h, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list) and len(r.json()) >= 2


def test_99_cleanup(admin_h):
    """Delete campaigns whose name contains 'Diretor'."""
    camps = requests.get(f"{BASE}/api/admin/campanhas", headers=admin_h, timeout=30).json()
    for c in camps:
        if "Diretor" in (c.get("nome") or ""):
            requests.delete(f"{BASE}/api/admin/campanhas/{c['id']}", headers=admin_h, timeout=30)
