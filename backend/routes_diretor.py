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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, require_role, audit, new_id, now_iso
from routes_data import since, enrich_campaigns

router = APIRouter(prefix="/diretor", dependencies=[Depends(require_role("admin"))])
MODEL = ("gemini", "gemini-2.5-flash")
WRITE_ACTIONS = {"criar_campanha", "gerar_contrato", "enviar_email", "gerar_qr_code", "propor_correcao"}

SYSTEM = ("És o Diretor Geral da RRClub. Falas português de Portugal. Tens três subagentes: Marketing (analisa campanhas), Frontend (analisa código UI), Backend (analisa código servidor). "
          "Usas as funções disponíveis para ler dados e executar ações. Ações que alteram dados vão para acoes_pendentes e só executam após aprovação do CEO. Nunca apagas dados. Sê conciso e direto.\n\n"
          "CONTEXTO DE NEGÓCIO (sabe sempre): a RRClub é uma plataforma de hotéis em Portugal. Modelo por venda: 80% hotel / 5% influencer / 10% RRClub / 5% desconto ao cliente. "
          "O Stripe Connect faz o split automático. Os QR codes geram o tracking (clique → QR baixado → venda). Os influencers ganham por performance (5% por venda).\n\n"
          "REGRAS DE CONDUTA:\n"
          "1) FOCO ÚNICO: faz apenas o que o CEO pediu. Não acrescentas melhorias, não desvias para outros assuntos nem outros ficheiros. Se pede a correção de um erro, tratas só desse erro.\n"
          "2) HONESTIDADE: se não encontras algo, dizes 'Não encontrei. Preciso de mais informação.' NUNCA inventas ficheiros, funções, linhas ou números.\n"
          "3) COMUNICAÇÃO CLARA: português de Portugal, simples e direto, sem jargão técnico — explica como se o CEO não fosse programador.\n"
          "4) MEMÓRIA: antes de propor uma ação, chama consultar_licoes() e respeita as lições das propostas rejeitadas pelo CEO.\n"
          "7) CRÉDITOS: cada subagente e cada auditoria gastam créditos do CEO. Só chamas subagentes quando o CEO pede explicitamente análise de código/marketing; para perguntas de dados usa as funções diretas (ler_dashboard, listar_*). Nunca chamas mais de um subagente por pedido sem o CEO pedir.\n"
          "5) DIFFS VÁLIDOS: antes de propor uma alteração de código, lê o ficheiro real com ler_codigo_github(caminho) (ou pelo subagente) e gera um diff git correto: cabeçalhos '--- a/caminho/ficheiro' e '+++ b/caminho/ficheiro' "
          "(caminho a partir da raiz do repositório, ex.: backend/core.py), bloco '@@ -linha_inicial,contagem +linha_inicial,contagem @@' com números reais, linhas removidas com '-', adicionadas com '+', e 3 linhas de contexto antes e depois.\n"
          "6) VALIDAÇÃO OBRIGATÓRIA: chama validar_diff(ficheiro, diff) antes de propor_correcao. Só propões se devolver valido=true. Se falhar, NÃO propões e dizes ao CEO: 'Não consigo aplicar esta alteração. Motivo: <motivo>.'\n\n"
          "PROTOCOLO OBRIGATÓRIO: responde SEMPRE com um único JSON válido, sem texto fora dele, numa destas formas:\n"
          '1) Para chamar uma função: {"funcao": "<nome>", "args": {...}}\n'
          '2) Para responder ao CEO: {"resposta": "<texto em PT-PT, conciso, com números concretos>"}\n'
          "Podes chamar várias funções em sequência (uma por resposta) antes de responder. Funções de escrita (criar_campanha, gerar_contrato, enviar_email, gerar_qr_code, propor_correcao) NÃO executam: ficam pendentes de aprovação — informa o CEO disso.\n"
          "REGRA: quando o CEO pede para criar, propor, gerar ou enviar algo, DEVES chamar a função de escrita correspondente (com ids reais obtidos via listar_hoteis/listar_influencers) — nunca apenas descrever a ação.\n\n"
          "FUNÇÕES:\n"
          "- ler_dashboard(): receita, cliques, conversão, ticket médio, influencers (30 dias)\n"
          "- listar_hoteis(): hotéis/parceiros com performance\n"
          "- analisar_performance_hotel(hotel_id)\n"
          "- criar_campanha(nome, hotel_id, influencer_id, data_inicio, data_fim, formato)\n"
          "- gerar_contrato(hotel_id, influencer_id, split, duracao)  # split ex: {\"hotel\":75,\"influencer\":5,\"rrclub\":10,\"stripe\":10}\n"
          "- enviar_email(destinatario, assunto, corpo)\n"
          "- gerar_qr_code(influencer_id, campanha_id)\n"
          "- consultar_financeiro(): IVA, Stripe fees, margens\n"
          "- listar_influencers()\n"
          "- subagente_marketing(pergunta): analisa campanhas, cliques, conversão, origens e propõe ações\n"
          "- subagente_frontend(pergunta): lê o código React em frontend/src e analisa UI/UX, bugs, melhorias (pode indicar ficheiro)\n"
          "- subagente_backend(pergunta): lê o código FastAPI em backend/ e analisa API, segurança, performance (pode indicar ficheiro)\n"
          "- listar_ficheiros_github(pasta): lista ficheiros/pastas do repositório GitHub do projeto (pasta vazia = raiz)\n"
          "- ler_codigo_github(caminho): devolve o conteúdo de um ficheiro do repositório GitHub (ex.: backend/server.py)\n"
          "- procurar_codigo_github(termo): procura um termo no código do repositório GitHub e devolve os ficheiros onde aparece\n"
          "- validar_diff(ficheiro, diff): verifica se o ficheiro existe, se as linhas do diff existem no código atual e se aplica com 'git apply --check'. Devolve {valido, motivo}.\n"
          "- consultar_licoes(): lições aprendidas de propostas rejeitadas pelo CEO (o que foi proposto, porquê rejeitado, o que fazer diferente)\n"
          "- propor_correcao(area, ficheiro, descricao, diff): coloca uma correção de código VALIDADA em ações pendentes (area: frontend|backend; ficheiro a partir da raiz, ex. backend/core.py; diff unified). NÃO altera código até aprovação. Recusada automaticamente se o diff não validar.\n"
          "Delega aos subagentes quando a pergunta envolver análise aprofundada; integra as conclusões deles na resposta final. Quando um subagente devolver 'correcao_sugerida', valida o diff e só depois chamas propor_correcao.")


class MsgIn(BaseModel):
    mensagem: str


async def ler_dashboard(**_):
    reds = await db.redemptions.find({"date": {"$gte": since(30)}}, NO_ID).to_list(20000)
    claims = await db.coupon_claims.count_documents({"date": {"$gte": since(30)}})
    rev = round(sum(r["amount"] for r in reds), 2)
    return {"janela": "30 dias", "receita": rev, "vendas": len(reds), "comissoes": round(sum(r["commission"] for r in reds), 2), "cliques": claims,
            "conversao_pct": round(len(reds) / claims * 100, 1) if claims else 0, "ticket_medio": round(rev / len(reds), 2) if reds else 0,
            "influencers_ativos": await db.influencers.count_documents({"status": "Ativo"}), "hoteis_ativos": await db.partners.count_documents({"status": "Ativo"}),
            "campanhas_ativas": await db.campaigns.count_documents({"status": "Ativa"})}


async def listar_hoteis(**_):
    parts = await db.partners.find({}, {"_id": 0, "id": 1, "nome": 1, "categoria": 1, "cidade": 1, "status": 1}).to_list(200)
    reds = await db.redemptions.find({"date": {"$gte": since(30)}}, {"_id": 0, "partner_id": 1, "amount": 1}).to_list(20000)
    for p in parts:
        mine = [r for r in reds if r["partner_id"] == p["id"]]
        p["vendas_30d"] = len(mine); p["receita_30d"] = round(sum(r["amount"] for r in mine), 2)
    return parts


async def listar_influencers(**_):
    return await db.influencers.find({}, {"_id": 0, "id": 1, "nome": 1, "handle": 1, "seguidores": 1, "status": 1, "email": 1}).to_list(200)


async def analisar_performance_hotel(hotel_id: str = "", **_):
    p = await db.partners.find_one({"id": hotel_id}, NO_ID)
    if not p:
        return {"erro": "hotel_id não encontrado; usa listar_hoteis()"}
    camps = await enrich_campaigns(await db.campaigns.find({"parceiro_id": hotel_id}, NO_ID).to_list(100))
    reds = await db.redemptions.find({"partner_id": hotel_id}, NO_ID).to_list(20000)
    claims = await db.coupon_claims.count_documents({"partner_id": hotel_id})
    return {"hotel": {k: p.get(k) for k in ("id", "nome", "categoria", "cidade", "status", "iban")}, "campanhas": [{k: c.get(k) for k in ("id", "nome", "cupom", "influencer", "desconto", "status", "uses", "claims")} for c in camps],
            "vendas": len(reds), "receita": round(sum(r["amount"] for r in reds), 2), "cliques": claims, "conversao_pct": round(len(reds) / claims * 100, 1) if claims else 0}


async def consultar_financeiro(**_):
    reds = await db.redemptions.find({"date": {"$gte": since(30)}}, NO_ID).to_list(20000)
    bruto = sum(r["amount"] for r in reds)
    return {"janela": "30 dias", "faturacao_bruta": round(bruto, 2), "iva_23pct_incluido": round(bruto - bruto / 1.23, 2), "stripe_fees_estimadas_10pct": round(bruto * 0.10, 2),
            "split": {"hotel_75pct": round(bruto * 0.75, 2), "influencer_5pct": round(bruto * 0.05, 2), "rrclub_10pct": round(bruto * 0.10, 2)}, "margem_rrclub": round(bruto * 0.10, 2), "vendas": len(reds)}


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
    ap = await asyncio.to_thread(_apply_patch, area if area in CODE_DIRS else rel.split("/")[0] if rel.split("/")[0] in CODE_DIRS else "backend", diff, True)
    return {"valido": ap["ok"], "motivo": "" if ap["ok"] else f"git apply --check falhou: {ap.get('erro', '')[:300]}"}


async def consultar_licoes(**_):
    items = await db.licoes_aprendidas.find({}, NO_ID).sort("timestamp", -1).to_list(20)
    return {"total": len(items), "licoes": items} if items else {"total": 0, "licoes": [], "nota": "ainda não há rejeições registadas"}


LIMITE_DIARIO_DEFAULT = 60


async def _llm_guard(origem: str, n: int = 1):
    from datetime import datetime as _dt
    hoje = _dt.now(timezone.utc).date().isoformat()
    cfg = await db.settings.find_one({"id": "diretor"}, NO_ID) or {}
    limite = int(cfg.get("limite_diario") or LIMITE_DIARIO_DEFAULT)
    usado = await db.llm_usage.count_documents({"dia": hoje})
    if usado + n > limite:
        raise HTTPException(status_code=429, detail=f"Limite diário de créditos IA atingido ({usado}/{limite} chamadas hoje). Aumente o limite em Definições do Diretor ou tente amanhã.")
    await db.llm_usage.insert_many([{"id": new_id("llm"), "dia": hoje, "origem": origem, "timestamp": now_iso()} for _ in range(n)])


async def uso_hoje() -> dict:
    hoje = datetime.now(timezone.utc).date().isoformat()
    cfg = await db.settings.find_one({"id": "diretor"}, NO_ID) or {}
    return {"hoje": await db.llm_usage.count_documents({"dia": hoje}), "limite": int(cfg.get("limite_diario") or LIMITE_DIARIO_DEFAULT),
            "por_origem": {o: await db.llm_usage.count_documents({"dia": hoje, "origem": o}) for o in ("diretor", "subagente", "auditoria")}}


async def _subagent(role: str, system: str, prompt: str) -> dict:
    await _llm_guard("subagente")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id(role), system_message=system).with_model("anthropic", "claude-sonnet-4-6")
    txt = await chat.send_message(UserMessage(text=prompt))
    return {"subagente": role, "analise": txt.strip()[:4000]}


async def subagente_marketing(pergunta: str = "Analisa as campanhas", **_):
    camps = await enrich_campaigns(await db.campaigns.find({}, NO_ID).to_list(100))
    claims = await db.coupon_claims.find({"date": {"$gte": since(30)}}, {"_id": 0, "coupon": 1, "origem": 1, "qr_downloaded": 1, "converted": 1}).to_list(20000)
    dash = await ler_dashboard()
    fin = await consultar_financeiro()
    data = {"dashboard": dash, "financeiro": fin, "campanhas": [{k: c.get(k) for k in ("nome", "cupom", "parceiro", "influencer", "desconto", "comissao", "status", "validade", "uses", "claims")} for c in camps],
            "origens": {o: sum(1 for c in claims if c.get("origem") == o) for o in {c.get("origem") for c in claims}},
            "qr_baixados": sum(1 for c in claims if c.get("qr_downloaded")), "convertidos": sum(1 for c in claims if c.get("converted"))}
    return await _subagent("Marketing", "És o subagente de Marketing da RRClub (cupões QR de influencers para hotéis/restaurantes premium). Português de Portugal, conciso, orientado a ações com números. Máx. 200 palavras.",
                           f"Pergunta do Diretor: {pergunta}\n\nDADOS:\n{json.dumps(data, ensure_ascii=False, default=str)[:12000]}")


async def subagente_frontend(pergunta: str = "Analisa a UI", ficheiro: str = "", **_):
    files = _pick_files("frontend", pergunta, ficheiro)
    return {**await _subagent("Frontend", "És o subagente Frontend da RRClub: especialista React/Tailwind. Analisas código real e apontas bugs, riscos de UX, acessibilidade e melhorias concretas com referência a ficheiro/linha. Português de Portugal, conciso (máx. 220 palavras). Se houver uma correção clara, termina com um bloco 'CORRECAO_SUGERIDA:' seguido de JSON {\"ficheiro\":..., \"descricao\":..., \"diff\": \"<unified diff curto>\"}.",
                              f"Pergunta do Diretor: {pergunta}\n\nÍNDICE (frontend/src): {', '.join(_code_index('frontend'))}\n\nCÓDIGO:\n{_code_read('frontend', files)}"), "ficheiros_lidos": files}


async def subagente_backend(pergunta: str = "Analisa a API", ficheiro: str = "", **_):
    files = _pick_files("backend", pergunta, ficheiro)
    return {**await _subagent("Backend", "És o subagente Backend da RRClub: especialista FastAPI/MongoDB/Stripe. Analisas código real e apontas bugs, falhas de segurança/autorização, performance e melhorias concretas com referência a ficheiro/função. Nunca reveles valores de segredos. Português de Portugal, conciso (máx. 220 palavras). Se houver uma correção clara, termina com um bloco 'CORRECAO_SUGERIDA:' seguido de JSON {\"ficheiro\":..., \"descricao\":..., \"diff\": \"<unified diff curto>\"}.",
                              f"Pergunta do Diretor: {pergunta}\n\nÍNDICE (backend/): {', '.join(_code_index('backend'))}\n\nCÓDIGO:\n{_code_read('backend', files)}"), "ficheiros_lidos": files}


READ_FUNCS = {"ler_dashboard": ler_dashboard, "listar_hoteis": listar_hoteis, "listar_influencers": listar_influencers, "analisar_performance_hotel": analisar_performance_hotel, "consultar_financeiro": consultar_financeiro,
              "subagente_marketing": subagente_marketing, "subagente_frontend": subagente_frontend, "subagente_backend": subagente_backend,
              "ler_codigo_github": ler_codigo_github, "listar_ficheiros_github": listar_ficheiros_github, "procurar_codigo_github": procurar_codigo_github,
              "validar_diff": validar_diff, "consultar_licoes": consultar_licoes}


def _parse(txt: str) -> dict:
    t = txt.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(t[t.index("{"): t.rindex("}") + 1])
    except Exception:
        return {"resposta": txt.strip()}


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
    await _llm_guard("diretor")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    hist = await db.conversas_diretor.find({}, NO_ID).sort("timestamp", -1).to_list(6)
    prior = "\n".join(f"CEO: {h['mensagem_user']}\nDiretor: {h['resposta_diretor']}" for h in reversed(hist))
    licoes = await db.licoes_aprendidas.find({}, NO_ID).sort("timestamp", -1).to_list(8)
    lic_txt = "\n".join(f"- Proposto: {l['proposto'][:120]} | Rejeitado porque: {l['motivo'][:120]} | Fazer diferente: {l['fazer_diferente'][:120]}" for l in licoes)
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("dir"), system_message=SYSTEM + (f"\n\nLIÇÕES APRENDIDAS (rejeições do CEO):\n{lic_txt}" if lic_txt else "")).with_model(*MODEL)
    text = (f"Contexto recente:\n{prior}\n\n" if prior else "") + f"Hoje: {datetime.now(timezone.utc).date().isoformat()}\nCEO: {body.mensagem}"
    chamadas, pendentes, resposta = [], [], None
    for _ in range(6):
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
                chamadas.append({"funcao": fn, "args": args, "resumo": (res.get("analise", "")[:600] if isinstance(res, dict) else "")})
                text = f"RESULTADO de {fn}({json.dumps(args, ensure_ascii=False)}):\n{json.dumps(res, ensure_ascii=False, default=str)[:9000]}\n\nContinua (outra função ou resposta final em JSON)."
            elif fn in WRITE_ACTIONS:
                if fn == "propor_correcao":
                    v = await validar_diff(args.get("ficheiro", ""), args.get("diff", ""), args.get("area", ""))
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
    resposta = resposta or "Não consegui concluir a análise. Tente reformular."
    conv = {"id": new_id("cv"), "mensagem_user": body.mensagem, "resposta_diretor": resposta, "chamadas": chamadas, "acoes_ids": [a["id"] for a in pendentes], "timestamp": now_iso(), "user_id": user["id"]}
    await db.conversas_diretor.insert_one(dict(conv))
    conv.pop("user_id", None)
    return {**conv, "acoes_pendentes": pendentes}


@router.get("/conversas")
async def conversas():
    items = await db.conversas_diretor.find({}, {"_id": 0, "user_id": 0}).sort("timestamp", -1).to_list(50)
    return list(reversed(items))


@router.get("/acoes")
async def acoes(status: str = ""):
    q = {"status": status} if status else {}
    return await db.acoes_pendentes.find(q, NO_ID).sort("timestamp", -1).to_list(100)


async def _executar(a: dict, user: dict) -> dict:
    d, tipo = a["dados_json"], a["tipo_acao"]
    if tipo == "criar_campanha":
        p = await db.partners.find_one({"id": d.get("hotel_id")}, NO_ID) or {}
        i = await db.influencers.find_one({"id": d.get("influencer_id")}, NO_ID) or {}
        camp = {"id": new_id("c"), "nome": d.get("nome") or "Campanha Diretor", "parceiro_id": d.get("hotel_id"), "parceiro": p.get("nome", "—"), "influencer_id": d.get("influencer_id"), "influencer": i.get("nome", "—"),
                "cupom": f"{(i.get('handle') or 'RR').strip('@')[:6].upper()}-{secrets.token_hex(2).upper()}", "desconto": float(d.get("desconto") or 10), "comissao": float(d.get("comissao") or 5),
                "validade": d.get("data_fim") or (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(), "data_inicio": d.get("data_inicio"), "formato": d.get("formato") or "QR", "status": "Ativa", "origem": "diretor", "created_at": now_iso()}
        await db.campaigns.insert_one(dict(camp))
        from realtime import emit
        emit("cupons_gerados", quantidade=1, cupom=camp["cupom"], campanha=camp["nome"], parceiro=camp["parceiro"], por="Diretor IA", ref=camp["id"])
        return {"campanha_id": camp["id"], "cupom": camp["cupom"], "qr_code_url": f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{camp['cupom']}"}
    if tipo == "gerar_contrato":
        p = await db.partners.find_one({"id": d.get("hotel_id")}, NO_ID) or {}
        i = await db.influencers.find_one({"id": d.get("influencer_id")}, NO_ID) or {}
        split = d.get("split") or {"hotel": 75, "influencer": 5, "rrclub": 10, "stripe": 10}
        clausulas = (f"CONTRATO DE PARCERIA RRCLUB\n\nEntre {p.get('nome', 'Hotel')} (\"Parceiro\") e {i.get('nome', 'Influencer')} (\"Influencer\"), mediado pela RRClub.\n"
                     f"1. Objeto: promoção de experiências do Parceiro através de cupões QR do Influencer.\n2. Duração: {d.get('duracao', '30 dias')}.\n"
                     f"3. Split por venda paga: Parceiro {split.get('hotel')}%, Influencer {split.get('influencer')}%, RRClub {split.get('rrclub')}%, Stripe {split.get('stripe')}%.\n"
                     "4. Pagamentos via Stripe Connect ou transferência IBAN mensal com extrato.\n5. Dados pessoais tratados conforme RGPD.\n6. Rescisão com 15 dias de aviso.\n\nGerado automaticamente pelo Diretor IA; sujeito a assinatura.")
        ct = {"id": new_id("ct"), "hotel_id": d.get("hotel_id"), "influencer_id": d.get("influencer_id"), "hotel": p.get("nome"), "influencer": i.get("nome"), "split_json": split, "clausulas_texto": clausulas, "status": "rascunho", "timestamp": now_iso()}
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


@router.get("/uso")
async def uso():
    files = [f for f in _code_index("backend") if f.startswith("routes_") or f in ("core.py", "realtime.py", "mailer.py", "storage.py")]
    return {**await uso_hoje(), "custo_auditoria": len(files)}


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
    return subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)


def _apply_patch(area: str, diff: str, check_only: bool = False) -> dict:
    if not diff.strip() or "@@" not in diff:
        return {"ok": False, "etapa": "validar", "erro": "O patch não é um diff unificado válido (sem hunks @@)."}
    if not diff.endswith("\n"):
        diff += "\n"
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
    tests_dir = os.path.join(ROOT, "tests")
    if py and any(fn.startswith("test_") for fn in os.listdir(tests_dir)):
        r = _run([sys.executable, "-m", "pytest", "-q", "-x", tests_dir], timeout=240)
        if r.returncode != 0:
            return {"ok": False, "etapa": "pytest", "erro": (r.stdout + r.stderr)[-800:]}
        return {"ok": True, "etapa": "pytest", "saida": r.stdout[-300:]}
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
            _run(["git", "apply", "-R", "--recount", *ap["opcoes"], ap["patch_tmp"]])
            result.update({"status": "revertida", "ficheiros": ap["ficheiros"], "etapa": ver["etapa"], "erro": ver["erro"]})
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
async def auditoria(user: dict = Depends(require_role("admin"))):
    files = [f for f in _code_index("backend") if f.startswith("routes_") or f in ("core.py", "realtime.py", "mailer.py", "storage.py")]
    await _llm_guard("auditoria", len(files))
    results = await asyncio.gather(*[_audit_file(f) for f in files])
    achados = [a for r in results for a in r]
    order = {"alta": 0, "media": 1, "baixa": 2}
    achados.sort(key=lambda a: order.get(a["severidade"], 3))
    doc = {"id": new_id("audit"), "timestamp": now_iso(), "ficheiros": files, "achados": achados,
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
