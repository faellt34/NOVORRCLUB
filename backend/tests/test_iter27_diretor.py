"""Testes integrados do Diretor: só por opção explícita e em instância local isolada.

Nunca executar contra a RRClub real. Credenciais são fornecidas pelo ambiente,
não ficam guardadas no código. Não há limpeza destrutiva de campanhas.
"""
import os
import uuid
from urllib.parse import urlparse

import pytest
import requests

BASE = os.getenv("RRCLUB_DIRECTOR_INTEGRATION_BASE_URL", "").rstrip("/")
UA = {"User-Agent": "Mozilla/5.0 rrclub-test"}
pytestmark = pytest.mark.skipif(
    os.getenv("RRCLUB_RUN_DIRECTOR_INTEGRATION_TESTS") != "1",
    reason="Teste com criação de campanhas: exige autorização explícita em base isolada",
)


@pytest.fixture(scope="module", autouse=True)
def isolated_backend_only():
    parsed = urlparse(BASE)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        pytest.fail("Testes integrados permitidos apenas em localhost isolado, nunca na produção")


def _credentials(role):
    prefix = "RRCLUB_TEST_ADMIN" if role == "admin" else "RRCLUB_TEST_PARTNER"
    email, password = os.getenv(prefix + "_EMAIL"), os.getenv(prefix + "_PASSWORD")
    if not email or not password:
        pytest.skip(f"Credenciais de teste ausentes: {prefix}_EMAIL e {prefix}_PASSWORD")
    return email, password


def _login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, headers=UA, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(*_credentials('admin'))}", **UA}


@pytest.fixture(scope="module")
def partner_h():
    return {"Authorization": f"Bearer {_login(*_credentials('partner'))}", **UA}


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
    name = f"Teste Diretor QA {uuid.uuid4().hex[:10]}"
    msg = (f"Cria uma campanha QR chamada '{name}' para o parceiro id {ids['hotel_id']} "
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


def test_04_gerar_contrato_pendente_rejeitar(admin_h, ids):
    msg = (f"Gera uma minuta entre o parceiro id {ids['hotel_id']} e o influencer id {ids['influencer_id']} "
           "com split parceiro 80, influencer 5, RRClub 10 e desconto seguidor 5, "
           "duração 90 dias. Chama gerar_contrato.")
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
