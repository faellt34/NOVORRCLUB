import asyncio
import base64
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import db, NO_ID, require_role, audit, new_id, now_iso
from routes_data import since, enrich_campaigns
from diretor_tools import consultar_logs, metricas_granulares, diagnosticar_sistema, briefing as _briefing
from diretor_estrategia import snapshot_currency, resumo_estrategico, is_new_p5, financial_state, amounts_minor, is_synthetic
from diretor_orcamento import LIMITE_DIARIO_DEFAULT, AUDITORIA_LOTE_MAX, MAX_PASSOS_CONVERSA, LimiteAtingido, reservar_quota_diaria, selecionar_lote_auditoria

router = APIRouter(prefix="/diretor", dependencies=[Depends(require_role("admin"))])
MODEL = ("gemini", "gemini-2.5-flash")
MODELOS = {
    "gemini": {"provider": "gemini", "model": "gemini-2.5-flash", "nome": "Gemini 2.5 Flash", "custo": "€", "nota": "rápido e económico (padrão)"},
    "gpt": {"provider": "openai", "model": "gpt-5-nano", "nome": "ChatGPT · GPT-5 nano", "custo": "€", "nota": "o GPT mais económico"},
    "claude": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001", "nome": "Claude Haiku 4.5", "custo": "€€", "nota": "equilíbrio qualidade/custo"},
}
WRITE_ACTIONS = {"criar_campanha", "gerar_contrato", "enviar_email", "gerar_qr_code", "propor_correcao"}

SYSTEM = ("És o Diretor Geral da RRClub. Falas português de Portugal. Coordenas sete especialidades: Executivo, Operações P5, Finanças BR, Finanças PT, Marketing, Pesquisa de Mercado e Engenharia/Segurança. Tens três subagentes LLM existentes: Marketing, Frontend e Backend; usa funções determinísticas para as outras áreas. "
          "Usas as funções disponíveis para ler dados e executar ações. Ações que alteram dados vão para acoes_pendentes e só executam após aprovação do CEO. Nunca apagas dados. Sê conciso e direto.\n\n"
          "CONTEXTO DE NEGÓCIO (sabe sempre): a RRClub liga influenciadores a restaurantes, comércio, serviços e hotéis no Brasil e Portugal. Cada campanha P5 com 5% de desconto sobre bruto prevê 80% do bruto para parceiro, 5% para influenciador, 10% para RRClub e 5% desconto, antes das taxas efetivas Stripe. Nunca somes EUR a BRL; consulta só pagamentos locais com webhook pago, exclui testes, disputas e reembolsos. Sem prova, o valor é desconhecido. "
          "O Stripe Connect só transfere quando pagamento, configuração e destinatários estão verificados; uma conta pendente não bloqueia outros parceiros. QR registra cliques e scans, mas não comprova pagamento. O influenciador tem 5% do bruto em venda elegível.\n\n"
          "REGRAS DE CONDUTA:\n"
          "1) FOCO ÚNICO: faz apenas o que o CEO pediu. Não acrescentas melhorias, não desvias para outros assuntos nem outros ficheiros. Se pede a correção de um erro, tratas só desse erro.\n"
          "2) HONESTIDADE: se não encontras algo, dizes 'Não encontrei. Preciso de mais informação.' NUNCA inventas ficheiros, funções, linhas ou números.\n"
          "3) COMUNICAÇÃO CLARA: português de Portugal, simples e direto, sem jargão técnico — explica como se o CEO não fosse programador.\n"
          "4) MEMÓRIA: antes de propor uma ação, chama consultar_licoes() e respeita as lições das propostas rejeitadas pelo CEO.\n"
          "7) CRÉDITOS: cada chamada tua, cada subagente e cada auditoria gastam créditos do CEO. Sê eficiente: resolve a maioria dos pedidos com no máximo 2 funções antes de responder; nunca repitas uma função com os mesmos argumentos; só chamas subagentes quando o CEO pede explicitamente análise de código/marketing; para perguntas de dados usa as funções diretas (ler_dashboard, listar_*, metricas_granulares, consultar_logs, diagnosticar_sistema). Nunca chamas mais de um subagente por pedido sem o CEO pedir.\n"
          "8) PROATIVIDADE INTELIGENTE: não esperas que o CEO adivinhe o que perguntar. Antes de responder a perguntas de desempenho, problemas, 'o que se passa', 'como estamos' ou pedidos vagos, investiga primeiro: chama diagnosticar_sistema() e/ou metricas_granulares(dimensao) para encontrar anomalias (erros 500, rotas lentas, hotéis sem Stripe Connect, campanhas com cliques mas sem QR/vendas, campanhas expiradas). "
          "Se o CEO reporta um erro ou algo 'não funciona', chama SEMPRE consultar_logs(nivel='error', termo=<palavra-chave>) antes de opinar — nunca adivinhes a causa sem ver os logs. Na resposta final, para além do que foi pedido, termina com uma secção curta 'Alertas:' com no máximo 3 pontos concretos que o CEO deve saber (só se existirem). Isto não é desvio de foco: é dever de informar.\n"
          "9) INTERPRETAÇÃO CORRETA DOS DADOS: (a) erros anteriores ao deploy atual podem não ter voltado a ocorrer, mas NÃO afirmes que estão corrigidos sem teste e evidência; (b) rotas com esperado=true (chamadas a IA) demoram 3-15s por natureza — não são problema de performance; (c) motor_patches='interno' é a solução definitiva e funcional, não um problema a resolver; (d) para 401 usa analise_401: com_token_expirado_ou_revogado = sessões caducadas (normal), sem_token/em_login em volume = tentativa suspeita.\n"
          "5) DIFFS VÁLIDOS: antes de propor uma alteração de código, lê o ficheiro real com ler_codigo_github(caminho) (ou pelo subagente) e gera um diff git correto: cabeçalhos '--- a/caminho/ficheiro' e '+++ b/caminho/ficheiro' "
          "(caminho a partir da raiz do repositório, ex.: backend/core.py), bloco '@@ -linha_inicial,contagem +linha_inicial,contagem @@' com números reais, linhas removidas com '-', adicionadas com '+', e 3 linhas de contexto antes e depois.\n"
          "6) VALIDAÇÃO OBRIGATÓRIA: chama validar_diff(ficheiro, diff) antes de propor_correcao. Só propões se devolver valido=true. Se falhar, NÃO propões e dizes ao CEO: 'Não consigo aplicar esta alteração. Motivo: <motivo>.'\n\n"
          "PROTOCOLO OBRIGATÓRIO: responde SEMPRE com um único JSON válido, sem texto fora dele, numa destas formas:\n"
          '1) Para chamar uma função: {"funcao": "<nome>", "args": {...}}\n'
          '2) Para responder ao CEO: {"resposta": "<texto em PT-PT, conciso, com números concretos>"}\n'
          "Podes chamar várias funções em sequência (uma por resposta) antes de responder. Funções de escrita (criar_campanha, gerar_contrato, enviar_email, gerar_qr_code, propor_correcao) NÃO executam: ficam pendentes de aprovação — informa o CEO disso.\n"
          "REGRA: quando o CEO pede para criar, propor, gerar ou enviar algo, DEVES chamar a função de escrita correspondente (com ids reais obtidos via listar_hoteis/listar_influencers) — nunca apenas descrever a ação.\n\n"
          "FUNÇÕES:\n"
          "- ler_dashboard(): pagamentos P5 confirmados por webhook local, segregados BRL/EUR, e funil observado; não confundir com vendas manuais.\n"
          "- resumo_estrategico(): relatório executivo BR/PT sem custo de IA, evidências e 3 prioridades.\n"
          "- financas_brasil(): Pix BRL, pagos e Connect, sem taxas inventadas.\n"
          "- financas_portugal(): EUR, pagos e Connect, sem IVA estimado.\n"
          "- operacoes_p5(): funil P5 por moeda e estados reais.\n"
          "- listar_hoteis(): hotéis/parceiros com performance\n"
          "- analisar_performance_hotel(hotel_id)\n"
          "- criar_campanha(nome, hotel_id, influencer_id, data_inicio, data_fim, formato)\n"
          "- gerar_contrato(hotel_id, influencer_id, split, duracao)  # split: {\"parceiro\":80,\"influencer\":5,\"rrclub\":10,\"desconto\":5} sobre o bruto, sujeito às taxas reais\n"
          "- enviar_email(destinatario, assunto, corpo)\n"
          "- gerar_qr_code(influencer_id, campanha_id)\n"
          "- consultar_financeiro(): relatório P5 por moeda e distinção entre pago local, Connect e banco.\n"
          "- listar_influencers()\n"
          "- subagente_marketing(pergunta): analisa campanhas, cliques, conversão, origens e propõe ações\n"
          "- subagente_frontend(pergunta): lê o código React em frontend/src e analisa UI/UX, bugs, melhorias (pode indicar ficheiro)\n"
          "- subagente_backend(pergunta): lê o código FastAPI em backend/ e analisa API, segurança, performance (pode indicar ficheiro)\n"
          "- listar_ficheiros_github(pasta): lista ficheiros/pastas do repositório GitHub do projeto (pasta vazia = raiz)\n"
          "- ler_codigo_github(caminho): devolve o conteúdo de um ficheiro do repositório GitHub (ex.: backend/server.py)\n"
          "- procurar_codigo_github(termo): procura um termo no código do repositório GitHub e devolve os ficheiros onde aparece\n"
          "- validar_diff(ficheiro, diff): verifica se o ficheiro existe, se as linhas do diff existem no código atual e se aplica com 'git apply --check'. Devolve {valido, motivo}.\n"
          "- consultar_licoes(): lições aprendidas de propostas rejeitadas pelo CEO (o que foi proposto, porquê rejeitado, o que fazer diferente)\n"
          "- consultar_logs(nivel, termo, horas, limite): logs detalhados do sistema (nivel: error|warn|''; termo filtra mensagem/rota/traceback; horas até 336). Devolve erros 500 com traceback, 4xx, pedidos lentos, rotas mais afetadas e auditoria recente. USA quando algo 'não funciona'.\n"
          "- metricas_granulares(dimensao, dias): atividade de QR e resgates (inclui histórico NÃO financeiro); para receitas reais utiliza resumo_estrategico.\n"
          "- diagnosticar_sistema(): saúde 24h (erros 500, 4xx, pedidos lentos, rotas mais lentas), estado Stripe (modo, hotéis sem Connect/incompletos, último pagamento) e operação (parceiros pendentes, campanhas expiradas/a expirar, ações pendentes).\n"
          "- propor_correcao(area, ficheiro, descricao, diff): coloca uma correção de código VALIDADA em ações pendentes (area: frontend|backend; ficheiro a partir da raiz, ex. backend/core.py; diff unified). NÃO altera código até aprovação. Recusada automaticamente se o diff não validar.\n"
          "Delega aos subagentes quando a pergunta envolver análise aprofundada; integra as conclusões deles na resposta final. Quando um subagente devolver 'correcao_sugerida', valida o diff e só depois chamas propor_correcao.")


class MsgIn(BaseModel):
    mensagem: str = Field(min_length=1, max_length=4000)
    modelo: str = "gemini"


async def ler_dashboard(**_):
    result = await resumo_estrategico()
    return {
        "janela": "30 dias", "fonte": "payment_transactions; exclui resgates manuais",
        "por_moeda": result["financeiro_por_pais"],
        "nota": "Não somar EUR e BRL; não chamar receita Stripe a resgates fictícios."
    }


async def listar_hoteis(**_):
    parts = await db.partners.find({}, {"_id": 0, "id": 1, "nome": 1, "categoria": 1, "cidade": 1, "status": 1, "currency": 1}).to_list(200)
    since_date = since(30)
    txs = await db.payment_transactions.find(
        {"created_at": {"$gte": since_date}, "payment_status": "paid"},
        {"_id": 0}
    ).to_list(20000)
    for p in parts:
        currency = str(p.get("currency") or "eur").lower()
        paid = [
            t for t in txs if t.get("partner_id") == p["id"]
            and is_new_p5(t, currency)
            and financial_state(t, currency) in ("transferido_connect", "pago_repasses_pendentes")
        ]
        p["vendas_p5_pagas_30d"] = len(paid)
        p["receita_p5_cobrada_30d"] = round(sum(amounts_minor(t, currency)["cobrado"] for t in paid) / 100, 2)
        p["receita_moeda"] = currency
    return parts


async def listar_influencers(**_):
    return await db.influencers.find({}, {"_id": 0, "id": 1, "nome": 1, "handle": 1, "seguidores": 1, "status": 1}).to_list(200)


async def analisar_performance_hotel(hotel_id: str = "", **_):
    partner = await db.partners.find_one({"id": hotel_id}, NO_ID)
    if not partner:
        return {"erro": "parceiro não encontrado; consulta listar_hoteis()"}
    currency = str(partner.get("currency") or "eur").lower()
    camps = await enrich_campaigns(await db.campaigns.find({"parceiro_id": hotel_id}, NO_ID).to_list(100))
    txs = await db.payment_transactions.find(
        {"partner_id": hotel_id, "currency": currency, "payment_status": "paid", "created_at": {"$gte": since(30)}},
        NO_ID
    ).to_list(20000)
    paid = [t for t in txs if is_new_p5(t, currency) and financial_state(t, currency) in ("transferido_connect", "pago_repasses_pendentes")]
    return {
        "parceiro": {k: partner.get(k) for k in ("id", "nome", "categoria", "cidade", "status", "currency")},
        "campanhas": [{k: c.get(k) for k in ("id", "nome", "cupom", "influencer", "desconto", "status")} for c in camps],
        "vendas_p5_pagas_30d": len(paid),
        "cobrado_p5_30d": round(sum(amounts_minor(t, currency)["cobrado"] for t in paid) / 100, 2),
        "currency": currency,
        "fonte": "pagamentos P5 locais pós-webhook; não equivale a saldo bancário",
    }


async def consultar_financeiro(**_):
    return {"brl": await snapshot_currency("brl"), "eur": await snapshot_currency("eur"),
            "nota": "Nunca somar moedas, estimar IVA ou criar tarifa Stripe fictícia."}


async def financas_brasil(**_):
    return await snapshot_currency("brl")


async def financas_portugal(**_):
    return await snapshot_currency("eur")


async def operacoes_p5(**_):
    data = await resumo_estrategico()
    return {"gerado_em": data["gerado_em"],
            "funis": {c: d["funil_observado"] for c, d in data["financeiro_por_pais"].items()},
            "estados": {c: d["estados_p5"] for c, d in data["financeiro_por_pais"].items()},
            "nota": "Clique, scan, checkout, pagamento e transferência são estados diferentes."}


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_DIRS = {"frontend": os.path.join(ROOT, "frontend", "src"), "backend": os.path.join(ROOT, "backend")}


def _code_index(area: str) -> list[str]:
    base, out = CODE_DIRS[area], []
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", "ui", "media")]
        for f in fns:
            if f.endswith((".jsx", ".js", ".py", ".css")) and not f.startswith("."):
                out.append(os.path.relpath(os.path.join(dp, f), base))
    return sorted(out)


def _code_read(area: str, files: list[str], budget: int = 24000) -> str:
    parts, used = [], 0
    for rel in files:
        p = os.path.normpath(os.path.join(CODE_DIRS[area], rel))
        if not p.startswith(CODE_DIRS[area]) or not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8", errors="ignore").read()
        chunk = txt[: max(0, min(len(txt), budget - used))]
        used += len(chunk)
        parts.append(f"===== {rel} ({len(txt)} chars) =====\n{chunk}")
        if used >= budget:
            break
    return "\n\n".join(parts)


def _pick_files(area: str, pergunta: str, ficheiro: str) -> list[str]:
    idx = _code_index(area)
    if ficheiro:
        hits = [f for f in idx if ficheiro.lower() in f.lower()]
        if hits:
            return hits[:3]
    words = [w.lower() for w in pergunta.replace("/", " ").split() if len(w) > 3]
    scored = sorted(idx, key=lambda f: -sum(1 for w in words if w in f.lower()))
    default = {"frontend": ["pages/AdminDashboard.jsx", "pages/PublicCoupon.jsx", "services/ws.js"], "backend": ["routes_data.py", "routes_payments.py", "realtime.py"]}[area]
    return list(dict.fromkeys(scored[:2] + default))[:4]


GH_REPO = os.environ.get("GITHUB_REPO", "")
GH_BRANCH = os.environ.get("GITHUB_BRANCH", "main")


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "rrclub-diretor"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


async def _gh(url: str, params: dict = None) -> tuple[int, object]:
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers=_gh_headers(), params=params)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"message": r.text[:200]}


def _gh_path(p: str) -> str:
    p = os.path.normpath("/" + str(p or "")).lstrip("/")
    return "" if p == "." else p


async def listar_ficheiros_github(pasta: str = "", **_):
    if not GH_REPO:
        return {"erro": "GITHUB_REPO não configurado"}
    st, data = await _gh(f"https://api.github.com/repos/{GH_REPO}/contents/{_gh_path(pasta)}", {"ref": GH_BRANCH})
    if st != 200:
        return {"erro": f"GitHub {st}: {data.get('message', '') if isinstance(data, dict) else ''}"}
    items = data if isinstance(data, list) else [data]
    return {"repo": GH_REPO, "branch": GH_BRANCH, "pasta": _gh_path(pasta) or "/", "itens": [{"nome": i["name"], "tipo": i["type"], "caminho": i["path"], "tamanho": i.get("size")} for i in items][:200]}


async def ler_codigo_github(caminho: str = "", **_):
    if not GH_REPO:
        return {"erro": "GITHUB_REPO não configurado"}
    path = _gh_path(caminho)
    if not path:
        return {"erro": "indica o caminho do ficheiro (ex.: backend/server.py)"}
    st, data = await _gh(f"https://api.github.com/repos/{GH_REPO}/contents/{path}", {"ref": GH_BRANCH})
    if st != 200 or not isinstance(data, dict) or data.get("type") != "file":
        return {"erro": f"ficheiro não encontrado ({st}); usa listar_ficheiros_github(pasta)"}
    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore") if data.get("encoding") == "base64" else ""
    return {"repo": GH_REPO, "caminho": path, "tamanho": data.get("size"), "sha": data.get("sha"), "conteudo": content[:20000], "truncado": len(content) > 20000}


async def procurar_codigo_github(termo: str = "", **_):
    if not GH_REPO:
        return {"erro": "GITHUB_REPO não configurado"}
    if not termo.strip():
        return {"erro": "indica o termo a procurar"}
    st, data = await _gh("https://api.github.com/search/code", {"q": f"{termo.strip()} repo:{GH_REPO}", "per_page": 20})
    if st == 200:
        return {"repo": GH_REPO, "termo": termo, "total": data.get("total_count", 0), "resultados": [{"ficheiro": i["path"], "nome": i["name"]} for i in data.get("items", [])]}
    st, tree = await _gh(f"https://api.github.com/repos/{GH_REPO}/git/trees/{GH_BRANCH}", {"recursive": "1"})
    if st != 200:
        return {"erro": f"GitHub {st}: {tree.get('message', '') if isinstance(tree, dict) else ''}"}
    t = termo.strip().lower()
    files = [i for i in tree.get("tree", []) if i["type"] == "blob" and "node_modules" not in i["path"] and i["path"].endswith((".py", ".js", ".jsx", ".css", ".md", ".json", ".yml", ".yaml", ".html"))]
    hits = [{"ficheiro": i["path"], "onde": "nome"} for i in files if t in i["path"].lower()]
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        for i in [f for f in files if (f.get("size") or 0) < 60000 and not any(h["ficheiro"] == f["path"] for h in hits)][:80]:
            r = await c.get(f"https://raw.githubusercontent.com/{GH_REPO}/{GH_BRANCH}/{i['path']}", headers=_gh_headers())
            if r.status_code == 200 and t in r.text.lower():
                ln = next((n for n, l in enumerate(r.text.splitlines(), 1) if t in l.lower()), None)
                hits.append({"ficheiro": i["path"], "onde": f"linha {ln}"})
            if len(hits) >= 20:
                break
    return {"repo": GH_REPO, "termo": termo, "total": len(hits), "resultados": hits, "nota": "pesquisa sem token: nome + conteúdo dos primeiros 80 ficheiros de código"}


async def validar_diff(ficheiro: str = "", diff: str = "", area: str = "", **_):
    diff = str(diff or "")
    rel = _gh_path(ficheiro)
    if not rel:
        return {"valido": False, "motivo": "indica o ficheiro (ex.: backend/core.py)"}
    if not os.path.isfile(os.path.join(ROOT, rel)):
        return {"valido": False, "motivo": f"o ficheiro {rel} não existe no projeto"}
    if not re.search(r"^--- a/.+\n\+\+\+ b/.+", diff, re.M):
        return {"valido": False, "motivo": "faltam os cabeçalhos '--- a/caminho' e '+++ b/caminho'"}
    if not re.search(r"^@@ -\d+(,\d+)? \+\d+(,\d+)? @@", diff, re.M):
        return {"valido": False, "motivo": "falta o bloco '@@ -linha,contagem +linha,contagem @@' com números reais"}
    src = open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore").read().splitlines()
    missing = [l[1:] for l in diff.splitlines() if l.startswith(("-", " ")) and not l.startswith("---") and l[1:].strip() and l[1:] not in src]
    if missing:
        return {"valido": False, "motivo": f"estas linhas não existem no ficheiro atual: {missing[:3]}"}
    if not await asyncio.to_thread(_git_ok):
        r = await asyncio.to_thread(_apply_patch, area if area in CODE_DIRS else "backend", diff, True)
        return {"valido": r["ok"], "motivo": "" if r["ok"] else f"motor interno: {r.get('erro', '')[:300]}", "nota": "validado pelo motor interno de patches (git indisponível)"}
    ap = await asyncio.to_thread(_apply_patch, area if area in CODE_DIRS else rel.split("/")[0] if rel.split("/")[0] in CODE_DIRS else "backend", diff, True)
    return {"valido": ap["ok"], "motivo": "" if ap["ok"] else f"git apply --check falhou: {ap.get('erro', '')[:300]}"}


async def consultar_licoes(**_):
    items = await db.licoes_aprendidas.find({}, NO_ID).sort("timestamp", -1).to_list(20)
    return {"total": len(items), "licoes": items} if items else {"total": 0, "licoes": [], "nota": "ainda não há rejeições registadas"}


async def _llm_guard(origem: str, n: int = 1):
    from datetime import datetime as _dt
    hoje = _dt.now(timezone.utc).date().isoformat()
    cfg = await db.settings.find_one({"id": "diretor"}, NO_ID) or {}
    limite = int(cfg.get("limite_diario") or LIMITE_DIARIO_DEFAULT)
    try:
        await reservar_quota_diaria(db.llm_quota, db.llm_usage, hoje, limite, n)
    except LimiteAtingido as e:
        raise HTTPException(status_code=429, detail=f"Limite diário de IA atingido ({e.usado}/{e.limite} chamadas hoje). Ajuste o limite ou tente amanhã.") from e
    await db.llm_usage.insert_many([{"id": new_id("llm"), "dia": hoje, "origem": origem, "timestamp": now_iso()} for _ in range(n)])


async def uso_hoje() -> dict:
    hoje = datetime.now(timezone.utc).date().isoformat()
    cfg = await db.settings.find_one({"id": "diretor"}, NO_ID) or {}
    quota = await db.llm_quota.find_one({"_id": f"diretor:{hoje}"}) or {}
    historico = await db.llm_usage.count_documents({"dia": hoje})
    return {"hoje": max(int(quota.get("usado", 0)), historico), "limite": int(cfg.get("limite_diario") or LIMITE_DIARIO_DEFAULT),
            "por_origem": {o: await db.llm_usage.count_documents({"dia": hoje, "origem": o}) for o in ("diretor", "subagente", "auditoria")}}


async def _subagent(role: str, system: str, prompt: str) -> dict:
    await _llm_guard("subagente")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    model = MODELOS["gemini"]  # Económico: não abrir Sonnet automaticamente por cada especialista.
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id(role), system_message=system).with_model(model["provider"], model["model"])
    txt = await chat.send_message(UserMessage(text=prompt))
    return {"subagente": role, "analise": txt.strip()[:4000]}


async def subagente_marketing(pergunta: str = "Analisa as campanhas", **_):
    camps = await enrich_campaigns(await db.campaigns.find({}, NO_ID).to_list(100))
    claims = await db.coupon_claims.find({"date": {"$gte": since(30)}}, {"_id": 0, "coupon": 1, "origem": 1, "qr_downloaded": 1, "converted": 1}).to_list(20000)
    dash = await ler_dashboard()
    fin = await consultar_financeiro()
    data = {"dashboard": dash, "financeiro": fin, "campanhas": [{k: c.get(k) for k in ("nome", "cupom", "parceiro", "influencer", "desconto", "comissao", "status", "validade", "uses", "claims")} for c in camps],
            "origens": {o: sum(1 for c in claims if c.get("origem") == o) for o in {c.get("origem") for c in claims}},
            "qr_baixados": sum(1 for c in claims if c.get("qr_downloaded")), "interacoes_convertidas_nao_e_pagamento": sum(1 for c in claims if c.get("converted"))}
    return await _subagent("Marketing", "És o subagente de Marketing da RRClub (cupões QR de influenciadores para negócios locais no Brasil e em Portugal). Só tratas números financeiros de pagamentos P5 locais pós-webhook, segregados em EUR e BRL. Não inferes que clique ou conversão de cupom significa venda paga. Português de Portugal, conciso, orientado a ações com números. Máx. 200 palavras.",
                           f"Pergunta do Diretor: {pergunta}\n\nDADOS:\n{json.dumps(data, ensure_ascii=False, default=str)[:12000]}")


async def subagente_frontend(pergunta: str = "Analisa a UI", ficheiro: str = "", **_):
    files = _pick_files("frontend", pergunta, ficheiro)
    return {**await _subagent("Frontend", "És o subagente Frontend da RRClub: especialista React/Tailwind. Analisas código real e apontas bugs, riscos de UX, acessibilidade e melhorias concretas com referência a ficheiro/linha. Português de Portugal, conciso (máx. 220 palavras). Se houver uma correção clara, termina com um bloco 'CORRECAO_SUGERIDA:' seguido de JSON {\"ficheiro\":..., \"descricao\":..., \"diff\": \"<unified diff curto>\"}.",
                              f"Pergunta do Diretor: {pergunta}\n\nÍNDICE (frontend/src): {', '.join(_code_index('frontend'))}\n\nCÓDIGO:\n{_code_read('frontend', files)}"), "ficheiros_lidos": files}


async def subagente_backend(pergunta: str = "Analisa a API", ficheiro: str = "", **_):
    files = _pick_files("backend", pergunta, ficheiro)
    return {**await _subagent("Backend", "És o subagente Backend da RRClub: especialista FastAPI/MongoDB/Stripe. Analisas código real e apontas bugs, falhas de segurança/autorização, performance e melhorias concretas com referência a ficheiro/função. Nunca reveles valores de segredos. Português de Portugal, conciso (máx. 220 palavras). Se houver uma correção clara, termina com um bloco 'CORRECAO_SUGERIDA:' seguido de JSON {\"ficheiro\":..., \"descricao\":..., \"diff\": \"<unified diff curto>\"}.",
                              f"Pergunta do Diretor: {pergunta}\n\nÍNDICE (backend/): {', '.join(_code_index('backend'))}\n\nCÓDIGO:\n{_code_read('backend', files)}"), "ficheiros_lidos": files}


READ_FUNCS = {"ler_dashboard": ler_dashboard, "resumo_estrategico": resumo_estrategico, "financas_brasil": financas_brasil, "financas_portugal": financas_portugal, "operacoes_p5": operacoes_p5, "listar_hoteis": listar_hoteis, "listar_influencers": listar_influencers, "analisar_performance_hotel": analisar_performance_hotel, "consultar_financeiro": consultar_financeiro,
              "subagente_marketing": subagente_marketing, "subagente_frontend": subagente_frontend, "subagente_backend": subagente_backend,
              "ler_codigo_github": ler_codigo_github, "listar_ficheiros_github": listar_ficheiros_github, "procurar_codigo_github": procurar_codigo_github,
              "validar_diff": validar_diff, "consultar_licoes": consultar_licoes, "consultar_logs": consultar_logs, "diagnosticar_sistema": diagnosticar_sistema}


def _parse(txt: str) -> dict:
    t = txt.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(t[t.index("{"): t.rindex("}") + 1])
    except Exception:
        pass
    m = re.search(r'"resposta"\s*:\s*"', t)
    if m:
        body = t[m.end():].rstrip().rstrip("}").rstrip().rstrip('"')
        try:
            body = json.loads(f'"{body}"')
        except Exception:
            pass
        return {"resposta": body.strip()}
    return {"resposta": t.strip('{}" \n')}


async def _queue(tipo: str, args: dict) -> dict:
    desc = {"criar_campanha": f"Criar campanha '{args.get('nome')}' ({args.get('formato', 'QR')}) {args.get('data_inicio', '')} → {args.get('data_fim', '')}",
            "gerar_contrato": f"Contrato hotel {args.get('hotel_id')} × influencer {args.get('influencer_id')} · split {json.dumps(args.get('split', {}), ensure_ascii=False)} · {args.get('duracao', '')}",
            "enviar_email": f"Email para {args.get('destinatario')}: {args.get('assunto')}",
            "gerar_qr_code": f"Gerar QR para influencer {args.get('influencer_id')} na campanha {args.get('campanha_id')}",
            "propor_correcao": f"Aplicar correção em {args.get('area', '?')}/{args.get('ficheiro', '?')}: {str(args.get('descricao', ''))[:140]}"}[tipo]
    a = {"id": new_id("ac"), "tipo_acao": tipo, "descricao": desc, "dados_json": args, "status": "pendente", "timestamp": now_iso()}
    await db.acoes_pendentes.insert_one(dict(a))
    return a


@router.post("/conversar")
async def conversar(body: MsgIn, user: dict = Depends(require_role("admin"))):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    hist = await db.conversas_diretor.find({"user_id": user["id"]}, NO_ID).sort("timestamp", -1).to_list(6)
    prior = "\n".join(f"CEO: {str(h.get('mensagem_user', ''))[:800]}\nDiretor: {str(h.get('resposta_diretor', ''))[:1000]}" for h in reversed(hist))
    licoes = await db.licoes_aprendidas.find({}, NO_ID).sort("timestamp", -1).to_list(8)
    lic_txt = "\n".join(f"- Proposto: {l['proposto'][:120]} | Rejeitado porque: {l['motivo'][:120]} | Fazer diferente: {l['fazer_diferente'][:120]}" for l in licoes)
    m = MODELOS.get(body.modelo, MODELOS["gemini"])
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("dir"), system_message=SYSTEM + (f"\n\nLIÇÕES APRENDIDAS (rejeições do CEO):\n{lic_txt}" if lic_txt else "")).with_model(m["provider"], m["model"])
    text = (f"Contexto recente:\n{prior}\n\n" if prior else "") + f"Hoje: {datetime.now(timezone.utc).date().isoformat()}\nCEO: {body.mensagem}"
    chamadas, pendentes, resposta = [], [], None
    try:
      for passo in range(MAX_PASSOS_CONVERSA):
        await _llm_guard("diretor")
        out = _parse(await chat.send_message(UserMessage(text=text)))
        if "funcao" in out:
            fn, args = out["funcao"], out.get("args") or {}
            if fn in READ_FUNCS:
                try:
                    res = await READ_FUNCS[fn](**args)
                except TypeError:
                    res = {"erro": "argumentos inválidos"}
                except HTTPException as e:
                    res = {"erro": e.detail}
                except Exception as e:
                    res = {"erro": f"falha interna em {fn}: {type(e).__name__}: {str(e)[:200]}"}
                chamadas.append({"funcao": fn, "args": args, "resumo": (res.get("analise", "")[:600] if isinstance(res, dict) else "")})
                text = f"RESULTADO de {fn}({json.dumps(args, ensure_ascii=False)}):\n{json.dumps(res, ensure_ascii=False, default=str)[:9000]}\n\n" + ("ÚLTIMA RESPOSTA: não chames mais nenhuma função. Resume já os resultados verificáveis para o CEO; indica o que não ficou comprovado. Responde apenas em JSON com a chave resposta." if passo >= MAX_PASSOS_CONVERSA - 2 else "Continua (outra função ou resposta final em JSON).")
            elif fn in WRITE_ACTIONS:
                if fn == "propor_correcao":
                    try:
                        v = await validar_diff(args.get("ficheiro", ""), args.get("diff", ""), args.get("area", ""))
                    except Exception as e:
                        v = {"valido": False, "motivo": f"validação indisponível: {type(e).__name__}"}
                    if not v["valido"]:
                        text = f"RECUSADO: o diff não é válido — {v['motivo']}. NÃO propões esta alteração. Diz ao CEO: 'Não consigo aplicar esta alteração. Motivo: {v['motivo']}.' Responde em JSON."
                        chamadas.append({"funcao": "validar_diff", "args": {"ficheiro": args.get("ficheiro")}, "resumo": v["motivo"]})
                        continue
                a = await _queue(fn, args)
                pendentes.append(a)
                text = f"A ação {fn} foi colocada em acoes_pendentes (id {a['id']}) e aguarda aprovação do CEO. Continua ou responde ao CEO em JSON."
            else:
                text = f"Função {fn} desconhecida. Usa apenas as funções listadas. Responde em JSON."
            continue
        resposta = out.get("resposta") or json.dumps(out, ensure_ascii=False)
        break
    except HTTPException as e:
      if e.status_code == 429 and pendentes:
        resposta = f"{e.detail} Foram guardadas {len(pendentes)} ações pendentes para sua aprovação; nenhuma foi executada."
      else:
        raise
    except Exception as e:
      resposta = f"Erro técnico ao processar o pedido ({type(e).__name__}). A equipa técnica foi notificada; tente novamente."
      from observability import record
      await record("error", "diretor", f"conversar falhou: {type(e).__name__}: {str(e)[:300]}", caminho="/api/diretor/conversar", status=200)
    if not resposta and chamadas:
        ferramentas = ", ".join(dict.fromkeys(item["funcao"] for item in chamadas))
        resposta = (f"Análise parcial: consultei {ferramentas}, mas o limite de passos de IA foi atingido "
                    "antes da conclusão. Não foi executada qualquer correção automática. "
                    "Consulte os resultados no painel ou peça uma análise mais específica.")
    resposta = resposta or "Não consegui concluir a análise. Tente reformular."
    conv = {"id": new_id("cv"), "mensagem_user": body.mensagem, "resposta_diretor": resposta, "chamadas": chamadas, "acoes_ids": [a["id"] for a in pendentes], "timestamp": now_iso(), "user_id": user["id"], "modelo": m["nome"]}
    await db.conversas_diretor.insert_one(dict(conv))
    conv.pop("user_id", None)
    return {**conv, "acoes_pendentes": pendentes}


@router.get("/conversas")
async def conversas(user: dict = Depends(require_role("admin"))):
    items = await db.conversas_diretor.find({"user_id": user["id"]}, {"_id": 0, "user_id": 0}).sort("timestamp", -1).to_list(50)
    return list(reversed(items))


@router.get("/estrategia")
async def estrategia(dias: int = 30):
    return await resumo_estrategico(dias)


@router.get("/briefing")
async def briefing():
    return await _briefing()


@router.get("/modelos")
async def modelos():
    return [{"id": k, **v} for k, v in MODELOS.items()]


@router.get("/logs")
async def logs(nivel: str = "", termo: str = "", horas: int = 24, limite: int = 60):
    return await consultar_logs(nivel, termo, horas, limite)


@router.get("/metricas")
async def metricas(dimensao: str = "campanha", dias: int = 30):
    return await resumo_estrategico(dias)  # Dados verificados, não redemptions manuais.



@router.get("/acoes")
async def acoes(status: str = ""):
    q = {"status": status} if status else {}
    return await db.acoes_pendentes.find(q, NO_ID).sort("timestamp", -1).to_list(100)


async def _executar(a: dict, user: dict) -> dict:
    d, tipo = a["dados_json"], a["tipo_acao"]
    if tipo == "criar_campanha":
        p = await db.partners.find_one({"id": d.get("hotel_id")}, NO_ID)
        i = await db.influencers.find_one({"id": d.get("influencer_id")}, NO_ID)
        if not p or not i:
            raise HTTPException(409, "É necessário parceiro e influenciador existentes; sem duplicar cadastros.")
        currency = str(p.get("currency") or "eur").lower()
        if currency not in ("eur", "brl"):
            raise HTTPException(409, "Moeda do parceiro inválida")
        if i.get("currency") and str(i["currency"]).lower() != currency:
            raise HTTPException(409, "Moeda do influenciador diferente da moeda do parceiro")
        name = str(d.get("nome") or "").strip()
        if not name or len(name) > 120:
            raise HTTPException(400, "O nome da campanha deve conter 1 a 120 caracteres")
        if float(d.get("desconto", 5)) != 5 or float(d.get("comissao", 5)) != 5:
            raise HTTPException(409, "Regra P5: desconto 5% e comissão influenciador 5%; rever no contrato antes de alterar")
        prior = await db.campaigns.find_one(
            {"nome": name, "parceiro_id": p["id"], "influencer_id": i["id"]}, NO_ID
        )
        if prior:
            return {"campanha_id": prior["id"], "cupom": prior.get("cupom"), "ja_existia": True}
        camp = {
            "id": new_id("c"), "nome": name, "parceiro_id": p["id"], "parceiro": p.get("nome", "—"),
            "influencer_id": i["id"], "influencer": i.get("nome", "—"), "currency": currency,
            "cupom": f"{(i.get('handle') or 'RR').strip('@')[:6].upper()}-{secrets.token_hex(2).upper()}",
            "desconto": 5.0, "comissao": 5.0,
            "validade": d.get("data_fim") or (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
            "data_inicio": d.get("data_inicio"), "formato": d.get("formato") or "QR", "status": "Ativa",
            "origem": "diretor", "created_at": now_iso(),
        }
        await db.campaigns.insert_one(dict(camp))
        from realtime import emit
        emit("cupons_gerados", quantidade=1, cupom=camp["cupom"], campanha=camp["nome"], parceiro=camp["parceiro"], por="Diretor IA", ref=camp["id"])
        return {"campanha_id": camp["id"], "cupom": camp["cupom"], "currency": currency,
                "qr_code_url": f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{camp['cupom']}",
                "nota": "Campanha criada após aprovação do admin. Repasse individual depende do Connect de cada beneficiário."}
    if tipo == "gerar_contrato":
        p = await db.partners.find_one({"id": d.get("hotel_id")}, NO_ID)
        i = await db.influencers.find_one({"id": d.get("influencer_id")}, NO_ID)
        if not p or not i:
            raise HTTPException(409, "Parceiro/influenciador não encontrados")
        split = {"parceiro": 80, "influencer": 5, "rrclub": 10, "desconto": 5}
        if d.get("split") and d["split"] != split:
            raise HTTPException(409, "Percentagens do contrato divergentes do P5; revisão manual necessária")
        clausulas = (
            f"MINUTA DE PARCERIA RRCLUB\n\nEntre {p.get('nome', 'Parceiro')} e "
            f"{i.get('nome', 'Influenciador')}, através da RRClub.\n"
            f"1. Campanha por QR em {p.get('currency', 'eur').upper()}; duração: {d.get('duracao', '30 dias')}.\n"
            "2. De cada compra bruta elegível: 5% de desconto ao seguidor, "
            "80% ao parceiro, 5% ao influenciador e 10% à RRClub.\n"
            "3. Tarifas de processamento reais não são percentual fixo; ver contrato e extratos.\n"
            "4. Transferências dependem da cobrança confirmada e contas Connect verificadas.\n"
            "5. Dados e cumprimento fiscal sujeitos à revisão jurídica e contabilística local.\n"
            "Minuta gerada pelo Diretor IA. Não equivale a contrato assinado."
        )
        ct = {"id": new_id("ct"), "hotel_id": p["id"], "influencer_id": i["id"],
              "hotel": p.get("nome"), "influencer": i.get("nome"), "split_json": split,
              "clausulas_texto": clausulas, "status": "rascunho", "timestamp": now_iso()}
        await db.contratos_gerados.insert_one(dict(ct))
        return {"contrato_id": ct["id"], "status": "rascunho"}
    if tipo == "enviar_email":
        from mailer import send_email
        ok = await send_email(d.get("destinatario", ""), d.get("assunto", "RRClub"), d.get("assunto", "RRClub"), d.get("corpo", ""))
        return {"enviado": bool(ok)}
    if tipo == "gerar_qr_code":
        c = await db.campaigns.find_one({"id": d.get("campanha_id")}, NO_ID)
        if not c:
            return {"erro": "campanha não encontrada"}
        url = f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{c['cupom']}"
        await db.campaigns.update_one({"id": c["id"]}, {"$set": {"qr_code_url": url}})
        return {"qr_code_url": url, "cupom": c["cupom"]}
    if tipo == "propor_correcao":
        pdir = os.path.join(ROOT, "memory", "patches")
        os.makedirs(pdir, exist_ok=True)
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", f"{a['id']}-{os.path.basename(str(d.get('ficheiro', 'correcao')))}")[:120] + ".patch"
        with open(os.path.join(pdir, fname), "w", encoding="utf-8") as f:
            f.write(f"# {d.get('area')}/{d.get('ficheiro')}\n# {d.get('descricao')}\n\n{d.get('diff', '')}")
        await db.correcoes_aprovadas.insert_one({"id": new_id("fx"), "acao_id": a["id"], **{k: d.get(k) for k in ("area", "ficheiro", "descricao", "diff")}, "patch_file": f"memory/patches/{fname}", "status": "aprovada_para_aplicar", "timestamp": now_iso()})
        return {"patch_file": f"memory/patches/{fname}", "nota": "Correção aprovada e guardada como patch; a aplicação ao código é feita pelo agente de desenvolvimento (peça 'aplica as correções aprovadas')."}
    return {"erro": "tipo desconhecido"}


@router.post("/acoes/{acao_id}/aprovar")
async def aprovar(acao_id: str, user: dict = Depends(require_role("admin"))):
    a = await db.acoes_pendentes.find_one({"id": acao_id, "status": "pendente"}, NO_ID)
    if not a:
        raise HTTPException(status_code=404, detail="Ação pendente não encontrada")
    lock = await db.acoes_pendentes.update_one({"id": acao_id, "status": "pendente"}, {"$set": {"status": "a_executar"}})
    if not lock.matched_count:
        raise HTTPException(status_code=409, detail="Ação já está a ser processada")
    try:
        res = await _executar(a, user)
    except Exception as e:
        await db.acoes_pendentes.update_one({"id": acao_id}, {"$set": {"status": "pendente"}})
        raise HTTPException(status_code=500, detail=f"Falha ao executar: {str(e)[:200]}")
    await db.acoes_pendentes.update_one({"id": acao_id}, {"$set": {"status": "aprovada", "resultado": res, "aprovada_em": now_iso(), "aprovada_por": user["nome"]}})
    await audit("DIRETOR", f"Aprovada: {a['descricao']}", user, acao_id)
    return {"ok": True, "resultado": res}


class RejeitarIn(BaseModel):
    motivo: str = ""
    fazer_diferente: str = ""


@router.post("/acoes/{acao_id}/rejeitar")
async def rejeitar(acao_id: str, body: RejeitarIn = RejeitarIn(), user: dict = Depends(require_role("admin"))):
    a = await db.acoes_pendentes.find_one({"id": acao_id, "status": "pendente"}, NO_ID)
    if not a:
        raise HTTPException(status_code=404, detail="Ação pendente não encontrada")
    await db.acoes_pendentes.update_one({"id": acao_id}, {"$set": {"status": "rejeitada", "rejeitada_em": now_iso(), "rejeitada_por": user["nome"], "motivo": body.motivo}})
    licao = {"id": new_id("lic"), "acao_id": acao_id, "tipo_acao": a["tipo_acao"], "proposto": a["descricao"], "motivo": body.motivo.strip() or "sem motivo indicado",
             "fazer_diferente": body.fazer_diferente.strip() or "confirmar com o CEO antes de propor algo semelhante", "timestamp": now_iso()}
    await db.licoes_aprendidas.insert_one(dict(licao))
    await audit("DIRETOR", f"Ação rejeitada pelo CEO: {body.motivo[:100]}", user, acao_id)
    return {"ok": True}


class ReconciliarIn(BaseModel):
    aplicadas_dev: list[str] = []
    rejeitar: dict[str, str] = {}


@router.post("/acoes/reconciliar")
async def reconciliar(body: ReconciliarIn, user: dict = Depends(require_role("admin"))):
    acs = await db.acoes_pendentes.find({"tipo_acao": "propor_correcao", "status": "aprovada", "aplicacao.status": {"$ne": "aplicada"}}, NO_ID).to_list(500)
    out = {"desatualizadas": 0, "validas": 0, "aplicadas_dev": 0, "rejeitadas": 0}
    for a in acs:
        if a["id"] in body.aplicadas_dev:
            await db.acoes_pendentes.update_one({"id": a["id"]}, {"$set": {"aplicacao": {"status": "aplicada", "onde": "desenvolvimento", "por": user["nome"], "timestamp": now_iso()}}})
            out["aplicadas_dev"] += 1; continue
        if a["id"] in body.rejeitar:
            motivo = body.rejeitar[a["id"]]
            await db.acoes_pendentes.update_one({"id": a["id"]}, {"$set": {"status": "rejeitada", "rejeitada_em": now_iso(), "rejeitada_por": user["nome"], "motivo": motivo}})
            await db.licoes_aprendidas.insert_one({"id": new_id("lic"), "acao_id": a["id"], "tipo_acao": "propor_correcao", "proposto": a["descricao"], "motivo": motivo, "fazer_diferente": "nunca fixar domínios/URLs no código; usar variáveis de ambiente", "timestamp": now_iso()})
            out["rejeitadas"] += 1; continue
        d = a.get("dados_json") or {}
        area = d.get("area") if d.get("area") in CODE_DIRS else "backend"
        r = await asyncio.to_thread(_apply_patch, area, str(d.get("diff") or ""), True)
        if r["ok"]:
            out["validas"] += 1
        else:
            await db.acoes_pendentes.update_one({"id": a["id"]}, {"$set": {"status": "desatualizada", "aplicacao": {"status": "desatualizada", "erro": r.get("erro", "")[:200], "timestamp": now_iso()}}})
            out["desatualizadas"] += 1
    await audit("DIRETOR", f"Reconciliação de correções: {out}", user)
    return out



@router.get("/uso")
async def uso():
    files = [f for f in _code_index("backend") if f.startswith("routes_") or f in ("core.py", "realtime.py", "mailer.py", "storage.py")]
    return {**await uso_hoje(), "custo_auditoria": min(AUDITORIA_LOTE_MAX, len(files)), "total_ficheiros": len(files)}


class LimiteIn(BaseModel):
    limite_diario: int


@router.post("/uso/limite")
async def set_limite(body: LimiteIn, user: dict = Depends(require_role("admin"))):
    if not 5 <= body.limite_diario <= 1000:
        raise HTTPException(status_code=400, detail="Limite entre 5 e 1000 chamadas/dia")
    await db.settings.update_one({"id": "diretor"}, {"$set": {"id": "diretor", "limite_diario": body.limite_diario}}, upsert=True)
    await audit("DIRETOR", f"Limite diário de créditos IA: {body.limite_diario}", user)
    return await uso_hoje()


@router.get("/licoes")
async def licoes():
    return await db.licoes_aprendidas.find({}, NO_ID).sort("timestamp", -1).to_list(100)


def _run(cmd: list, cwd: str = None, timeout: int = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, "", f"'{cmd[0]}' não está disponível neste ambiente (produção). Alterações de código só podem ser aplicadas no ambiente de desenvolvimento.")


def _git_ok() -> bool:
    return _run(["git", "--version"]).returncode == 0


def _apply_internal(area: str, diff: str, check_only: bool) -> dict:
    import patch_engine
    roots = [ROOT, CODE_DIRS.get(area, CODE_DIRS["backend"]), CODE_DIRS["backend"], CODE_DIRS["frontend"]]
    backup = {}
    for f in patch_engine.parse(diff):
        name = f["new"] or f["old"]
        for base in roots:
            for st in (1, 0, 2):
                p = os.path.join(base, patch_engine._rel(name, st))
                if os.path.isfile(p):
                    backup[os.path.relpath(p, ROOT)] = open(p, encoding="utf-8", errors="ignore").read(); break
    r = patch_engine.run(diff, ROOT, 1, write=not check_only, roots=roots)
    if not r["ok"]:
        return {"ok": False, "etapa": "motor interno (sem git)", "erro": r["erro"]}
    return {"ok": True, "opcoes": ["interno"], "patch_tmp": None, "ficheiros": r["ficheiros"], "backup": backup, "motor": "interno"}


def _revert(ap: dict):
    if ap.get("motor") == "interno":
        for rel, content in ap.get("backup", {}).items():
            with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
                fh.write(content)
    else:
        _run(["git", "apply", "-R", "--recount", *ap["opcoes"], ap["patch_tmp"]])


def _apply_patch(area: str, diff: str, check_only: bool = False) -> dict:
    if not diff.strip() or "@@" not in diff:
        return {"ok": False, "etapa": "validar", "erro": "O patch não é um diff unificado válido (sem hunks @@)."}
    if not diff.endswith("\n"):
        diff += "\n"
    if not _git_ok():
        return _apply_internal(area, diff, check_only)
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as f:
        f.write(diff)
        pf = f.name
    sub = os.path.relpath(CODE_DIRS[area], ROOT)
    tries = [[], ["--directory", sub], ["-p0"], ["-p2", "--directory", sub], ["--directory", sub, "--ignore-whitespace"], ["--ignore-whitespace"]]
    for extra in tries:
        chk = _run(["git", "apply", "--check", "--recount", *extra, pf])
        if chk.returncode == 0:
            if check_only:
                os.unlink(pf)
                return {"ok": True, "opcoes": extra}
            res = _run(["git", "apply", "--recount", *extra, pf])
            if res.returncode == 0:
                names = _run(["git", "apply", "--numstat", "--recount", *extra, pf]).stdout
                files = [ln.split("\t")[-1] for ln in names.strip().splitlines() if ln.strip()]
                return {"ok": True, "opcoes": extra, "patch_tmp": pf, "ficheiros": files}
    os.unlink(pf)
    return {"ok": False, "etapa": "git apply --check", "erro": (chk.stderr or chk.stdout)[:600]}


def _verify(files: list) -> dict:
    py = [f for f in files if f.endswith(".py")]
    for f in py:
        r = _run([sys.executable, "-m", "py_compile", os.path.join(ROOT, f)])
        if r.returncode != 0:
            return {"ok": False, "etapa": "py_compile", "erro": r.stderr[-600:]}
    if py:
        r = _run([sys.executable, "-c", "import server"], cwd=CODE_DIRS["backend"], timeout=90)
        if r.returncode != 0:
            return {"ok": False, "etapa": "import server", "erro": r.stderr[-600:]}
    # Nunca executar em produção a suite completa: contém testes de integração
    # que criam campanhas e requerem uma instância local isolada.
    safe_tests = ("tests.test_diretor_estrategia", "tests.test_diretor_parceiros", "tests.test_diretor_test_safety", "tests.test_diretor_orcamento")
    if py:
        r = _run([sys.executable, "-m", "unittest", *safe_tests], cwd=CODE_DIRS["backend"], timeout=60)
        if r.returncode != 0:
            return {"ok": False, "etapa": "unittest_seguro", "erro": (r.stdout + r.stderr)[-800:]}
        return {"ok": True, "etapa": "unittest_seguro", "saida": (r.stdout + r.stderr)[-300:]}
    return {"ok": True, "etapa": "py_compile + import server" if py else "sem verificação automática para estes ficheiros", "saida": ""}


@router.post("/acoes/{acao_id}/aplicar")
async def aplicar_correcao(acao_id: str, user: dict = Depends(require_role("admin"))):
    a = await db.acoes_pendentes.find_one({"id": acao_id, "tipo_acao": "propor_correcao", "status": "aprovada"}, NO_ID)
    if not a:
        raise HTTPException(status_code=404, detail="Correção aprovada não encontrada")
    if (a.get("aplicacao") or {}).get("status") == "aplicada":
        raise HTTPException(status_code=409, detail="Correção já aplicada")
    d = a["dados_json"]
    area = d.get("area") if d.get("area") in CODE_DIRS else "backend"
    ap = await asyncio.to_thread(_apply_patch, area, str(d.get("diff") or ""))
    result = {"timestamp": now_iso(), "por": user["nome"]}
    if not ap["ok"]:
        result.update({"status": "falhou", **{k: ap[k] for k in ("etapa", "erro")}})
    else:
        ver = await asyncio.to_thread(_verify, ap["ficheiros"])
        if ver["ok"]:
            result.update({"status": "aplicada", "ficheiros": ap["ficheiros"], "verificacao": ver["etapa"], "saida": ver.get("saida", "")})
        else:
            _revert(ap)
            result.update({"status": "revertida", "ficheiros": ap["ficheiros"], "etapa": ver["etapa"], "erro": ver["erro"]})
        if ap.get("patch_tmp"):
            os.unlink(ap["patch_tmp"])
    await db.acoes_pendentes.update_one({"id": acao_id}, {"$set": {"aplicacao": result}})
    await db.correcoes_aprovadas.update_one({"acao_id": acao_id}, {"$set": {"status": result["status"], "aplicacao": result}})
    await audit("CORRECAO", f"Patch {result['status']}: {a['descricao'][:120]}", user, acao_id)
    return result


@router.get("/contratos")
async def contratos():
    return await db.contratos_gerados.find({}, NO_ID).sort("timestamp", -1).to_list(100)


async def _audit_file(rel: str) -> list:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    code = _code_read("backend", [rel], budget=30000)
    sys_msg = ("És o subagente Backend da RRClub (FastAPI/MongoDB/Stripe/JWT). Faz auditoria de segurança do ficheiro dado. Devolve APENAS JSON: "
               '{"achados":[{"severidade":"alta|media|baixa","funcao":"...","titulo":"...","descricao":"...","correcao":"...","diff":"<unified diff curto ou vazio>"}]}. '
               "Foca-te em: autenticação/autorização em falta, IDOR, validação de input, segredos, injeção, rate limiting, exposição de dados, idempotência financeira. Máx. 6 achados, os mais relevantes. Português de Portugal. Sem achados → lista vazia.")
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("aud"), system_message=sys_msg).with_model("anthropic", "claude-sonnet-4-6")
    try:
        out = _parse(await chat.send_message(UserMessage(text=f"FICHEIRO backend/{rel}\n\n{code}")))
        items = out.get("achados", []) if isinstance(out, dict) else []
    except Exception as e:
        items = [{"severidade": "baixa", "funcao": "-", "titulo": "Falha na análise", "descricao": str(e)[:200], "correcao": "", "diff": ""}]
    return [{"id": new_id("fd"), "ficheiro": rel, **{k: str(i.get(k, "")) for k in ("severidade", "funcao", "titulo", "descricao", "correcao", "diff")}} for i in items if isinstance(i, dict)]


@router.post("/auditoria")
async def auditoria(inicio: int = Query(0, ge=0), limite_ficheiros: int = Query(AUDITORIA_LOTE_MAX, ge=1, le=AUDITORIA_LOTE_MAX), user: dict = Depends(require_role("admin"))):
    todos = [f for f in _code_index("backend") if f.startswith("routes_") or f in ("core.py", "realtime.py", "mailer.py", "storage.py")]
    lote = selecionar_lote_auditoria(todos, inicio, limite_ficheiros)
    files = lote["ficheiros"]
    if not files:
        raise HTTPException(status_code=400, detail="Lote de auditoria vazio; recomece no início 0")
    await _llm_guard("auditoria", len(files))
    results = await asyncio.gather(*[_audit_file(f) for f in files])
    achados = [a for r in results for a in r]
    order = {"alta": 0, "media": 1, "baixa": 2}
    achados.sort(key=lambda a: order.get(a["severidade"], 3))
    doc = {"id": new_id("audit"), "timestamp": now_iso(), "ficheiros": files, "achados": achados,
           "inicio": lote["inicio"], "proximo_inicio": lote["proximo_inicio"], "total_ficheiros": lote["total"],
           "resumo": {k: sum(1 for a in achados if a["severidade"] == k) for k in ("alta", "media", "baixa")}, "por": user["nome"]}
    await db.auditorias.insert_one(dict(doc))
    await audit("AUDITORIA", f"Auditoria de segurança: {len(achados)} achados em {len(files)} ficheiros", user, doc["id"])
    return doc


@router.get("/auditoria")
async def auditoria_ultima():
    return await db.auditorias.find_one({}, NO_ID, sort=[("timestamp", -1)]) or {}


@router.post("/auditoria/{audit_id}/propor/{finding_id}")
async def propor_from_finding(audit_id: str, finding_id: str, user: dict = Depends(require_role("admin"))):
    doc = await db.auditorias.find_one({"id": audit_id}, NO_ID)
    f = next((a for a in (doc or {}).get("achados", []) if a["id"] == finding_id), None)
    if not f:
        raise HTTPException(status_code=404, detail="Achado não encontrado")
    a = await _queue("propor_correcao", {"area": "backend", "ficheiro": f["ficheiro"], "descricao": f"[{f['severidade']}] {f['titulo']} — {f['correcao']}", "diff": f.get("diff") or "", "finding_id": finding_id})
    await db.auditorias.update_one({"id": audit_id, "achados.id": finding_id}, {"$set": {"achados.$.acao_id": a["id"]}})
    return a
