import json
import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, NO_ID, require_role, audit, new_id, now_iso
from routes_data import since, enrich_campaigns

router = APIRouter(prefix="/diretor", dependencies=[Depends(require_role("admin"))])
MODEL = ("gemini", "gemini-2.5-flash")
WRITE_ACTIONS = {"criar_campanha", "gerar_contrato", "enviar_email", "gerar_qr_code"}

SYSTEM = ("És o Diretor Geral da RRClub. Falas português de Portugal. Tens três subagentes: Marketing (analisa campanhas), Frontend (analisa código UI), Backend (analisa código servidor). "
          "Usas as funções disponíveis para ler dados e executar ações. Ações que alteram dados vão para acoes_pendentes e só executam após aprovação do CEO. Nunca apagas dados. Sê conciso e direto.\n\n"
          "PROTOCOLO OBRIGATÓRIO: responde SEMPRE com um único JSON válido, sem texto fora dele, numa destas formas:\n"
          '1) Para chamar uma função: {"funcao": "<nome>", "args": {...}}\n'
          '2) Para responder ao CEO: {"resposta": "<texto em PT-PT, conciso, com números concretos>"}\n'
          "Podes chamar várias funções em sequência (uma por resposta) antes de responder. Funções de escrita (criar_campanha, gerar_contrato, enviar_email, gerar_qr_code) NÃO executam: ficam pendentes de aprovação — informa o CEO disso.\n"
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
          "- listar_influencers()")


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


READ_FUNCS = {"ler_dashboard": ler_dashboard, "listar_hoteis": listar_hoteis, "listar_influencers": listar_influencers, "analisar_performance_hotel": analisar_performance_hotel, "consultar_financeiro": consultar_financeiro}


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
            "gerar_qr_code": f"Gerar QR para influencer {args.get('influencer_id')} na campanha {args.get('campanha_id')}"}[tipo]
    a = {"id": new_id("ac"), "tipo_acao": tipo, "descricao": desc, "dados_json": args, "status": "pendente", "timestamp": now_iso()}
    await db.acoes_pendentes.insert_one(dict(a))
    return a


@router.post("/conversar")
async def conversar(body: MsgIn, user: dict = Depends(require_role("admin"))):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    hist = await db.conversas_diretor.find({}, NO_ID).sort("timestamp", -1).to_list(6)
    prior = "\n".join(f"CEO: {h['mensagem_user']}\nDiretor: {h['resposta_diretor']}" for h in reversed(hist))
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("dir"), system_message=SYSTEM).with_model(*MODEL)
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
                chamadas.append({"funcao": fn, "args": args})
                text = f"RESULTADO de {fn}({json.dumps(args, ensure_ascii=False)}):\n{json.dumps(res, ensure_ascii=False, default=str)[:6000]}\n\nContinua (outra função ou resposta final em JSON)."
            elif fn in WRITE_ACTIONS:
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
    return {"erro": "tipo desconhecido"}


@router.post("/acoes/{acao_id}/aprovar")
async def aprovar(acao_id: str, user: dict = Depends(require_role("admin"))):
    a = await db.acoes_pendentes.find_one({"id": acao_id, "status": "pendente"}, NO_ID)
    if not a:
        raise HTTPException(status_code=404, detail="Ação pendente não encontrada")
    res = await _executar(a, user)
    await db.acoes_pendentes.update_one({"id": acao_id}, {"$set": {"status": "aprovada", "resultado": res, "aprovada_em": now_iso(), "aprovada_por": user["nome"]}})
    await audit("DIRETOR", f"Aprovada: {a['descricao']}", user, acao_id)
    return {"ok": True, "resultado": res}


@router.post("/acoes/{acao_id}/rejeitar")
async def rejeitar(acao_id: str, user: dict = Depends(require_role("admin"))):
    r = await db.acoes_pendentes.update_one({"id": acao_id, "status": "pendente"}, {"$set": {"status": "rejeitada", "rejeitada_em": now_iso(), "rejeitada_por": user["nome"]}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Ação pendente não encontrada")
    await audit("DIRETOR", "Ação rejeitada pelo CEO", user, acao_id)
    return {"ok": True}


@router.get("/contratos")
async def contratos():
    return await db.contratos_gerados.find({}, NO_ID).sort("timestamp", -1).to_list(100)
