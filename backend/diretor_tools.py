import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from core import db, NO_ID
from routes_data import since

ARRANQUE = datetime.now(timezone.utc).isoformat()
ROTAS_IA = ("/api/diretor/conversar", "/api/diretor/auditoria", "/api/ai/")

DIMENSOES = {"campanha": ("campaign_id", "campaigns"), "influencer": ("influencer_id", "influencers"), "hotel": ("partner_id", "partners")}


def _pct(a, b):
    return round(a / b * 100, 1) if b else 0.0


async def consultar_logs(nivel: str = "", termo: str = "", horas: int = 24, limite: int = 40, **_):
    horas, limite = min(int(horas or 24), 336), min(int(limite or 40), 100)
    q = {"timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()}}
    if nivel in ("error", "warn", "info"):
        q["nivel"] = nivel
    if termo:
        q["$or"] = [{"mensagem": {"$regex": termo, "$options": "i"}}, {"caminho": {"$regex": termo, "$options": "i"}}, {"traceback": {"$regex": termo, "$options": "i"}}]
    items = await db.system_logs.find(q, {"_id": 0, "ts": 0}).sort("timestamp", -1).to_list(limite)
    for i in items:
        if i.get("traceback"):
            i["traceback"] = i["traceback"][-600:]
        i["anterior_ao_deploy_atual"] = i["timestamp"] < ARRANQUE
    por_nivel = {n: await db.system_logs.count_documents({**q, "nivel": n}) for n in ("error", "warn")}
    por_rota = defaultdict(int)
    por_ip = defaultdict(int)
    for i in items:
        if i.get("caminho"):
            por_rota[f"{i.get('metodo')} {i['caminho']}"] += 1
        if i.get("ip"):
            por_ip[i["ip"]] += 1
    n401 = [i for i in items if i.get("status") == 401]
    auth401 = {"total": len(n401), "com_token_expirado_ou_revogado": sum(1 for i in n401 if i.get("com_token")), "sem_token": sum(1 for i in n401 if i.get("com_token") is False),
               "em_login": sum(1 for i in n401 if "/auth/login" in (i.get("caminho") or "")), "ips": dict(__import__("collections").Counter(i["ip"] for i in n401 if i.get("ip")).most_common(5))}
    aud = await db.audit_log.find({"timestamp": q["timestamp"]} if not termo else {"timestamp": q["timestamp"], "detail": {"$regex": termo, "$options": "i"}}, NO_ID).sort("timestamp", -1).to_list(15)
    return {"janela_horas": horas, "arranque_do_servidor": ARRANQUE, "nota": "logs com anterior_ao_deploy_atual=true são da versão antiga, já substituída; não os reportes como problemas persistentes", "totais": por_nivel, "rotas_mais_afetadas": dict(sorted(por_rota.items(), key=lambda x: -x[1])[:8]), "ips_mais_frequentes": dict(sorted(por_ip.items(), key=lambda x: -x[1])[:5]),
            "analise_401": auth401, "logs": items, "auditoria_recente": aud}


async def metricas_granulares(dimensao: str = "campanha", dias: int = 30, **_):
    if dimensao == "qr":
        return await _metricas_qr(int(dias or 30))
    if dimensao not in DIMENSOES:
        return {"erro": "dimensao inválida; usa campanha | influencer | hotel | qr"}
    key, coll = DIMENSOES[dimensao]
    dias = int(dias or 30)
    s = since(dias)
    ents = {e["id"]: e async for e in db[coll].find({}, NO_ID)}
    rows = {eid: {"id": eid, "nome": e.get("nome"), "status": e.get("status"), "cliques": 0, "qr_baixados": 0, "vendas": 0, "receita": 0.0, "comissao": 0.0} for eid, e in ents.items()}
    if dimensao == "campanha":
        for eid, e in ents.items():
            rows[eid].update({"cupom": e.get("cupom"), "hotel": e.get("parceiro"), "influencer": e.get("influencer"), "validade": e.get("validade")})
    async for c in db.coupon_claims.find({"date": {"$gte": s}}, {"_id": 0, key: 1}):
        if c.get(key) in rows:
            rows[c[key]]["cliques"] += 1
    async for d in db.qr_downloads.find({"date": {"$gte": s}}, {"_id": 0, key: 1}):
        if d.get(key) in rows:
            rows[d[key]]["qr_baixados"] += 1
    async for r in db.redemptions.find({"date": {"$gte": s}}, {"_id": 0, key: 1, "amount": 1, "commission": 1}):
        if r.get(key) in rows:
            row = rows[r[key]]
            row["vendas"] += 1; row["receita"] += r.get("amount", 0); row["comissao"] += r.get("commission", 0)
    out = []
    for r in rows.values():
        r["receita"] = round(r["receita"], 2); r["comissao"] = round(r["comissao"], 2)
        r["taxa_qr_pct"] = _pct(r["qr_baixados"], r["cliques"]); r["conversao_pct"] = _pct(r["vendas"], r["cliques"]); r["ticket_medio"] = round(r["receita"] / r["vendas"], 2) if r["vendas"] else 0
        r["alerta"] = ("sem cliques" if not r["cliques"] else "cliques sem QR baixado" if not r["qr_baixados"] else "QR baixados sem vendas" if not r["vendas"] else None)
        out.append(r)
    out.sort(key=lambda x: (-x["receita"], -x["cliques"]))
    tot = {"cliques": sum(r["cliques"] for r in out), "qr_baixados": sum(r["qr_baixados"] for r in out), "vendas": sum(r["vendas"] for r in out), "receita": round(sum(r["receita"] for r in out), 2)}
    return {"dimensao": dimensao, "janela_dias": dias, "total": tot, "itens": out[:40]}


async def _metricas_qr(dias: int):
    s = since(dias)
    claims = await db.coupon_claims.find({"date": {"$gte": s}}, {"_id": 0, "origem": 1, "qr_downloaded": 1, "converted": 1, "date": 1, "converted_at": 1, "qr_downloaded_at": 1}).to_list(50000)
    por_origem = defaultdict(lambda: {"cliques": 0, "qr_baixados": 0, "vendas": 0})
    tempos = []
    for c in claims:
        o = por_origem[c.get("origem") or "—"]
        o["cliques"] += 1; o["qr_baixados"] += bool(c.get("qr_downloaded")); o["vendas"] += bool(c.get("converted"))
        if c.get("qr_downloaded_at") and c.get("converted_at"):
            try:
                tempos.append((datetime.fromisoformat(c["converted_at"]) - datetime.fromisoformat(c["qr_downloaded_at"])).total_seconds() / 3600)
            except Exception:
                pass
    por_dia = defaultdict(lambda: {"cliques": 0, "qr_baixados": 0, "vendas": 0})
    for c in claims:
        d = por_dia[c["date"][:10]]
        d["cliques"] += 1; d["qr_baixados"] += bool(c.get("qr_downloaded")); d["vendas"] += bool(c.get("converted"))
    n, q, v = len(claims), sum(1 for c in claims if c.get("qr_downloaded")), sum(1 for c in claims if c.get("converted"))
    return {"dimensao": "qr", "janela_dias": dias, "funil": {"cliques": n, "qr_baixados": q, "vendas": v, "taxa_qr_pct": _pct(q, n), "conversao_qr_venda_pct": _pct(v, q), "conversao_total_pct": _pct(v, n)},
            "tempo_medio_qr_ate_venda_horas": round(sum(tempos) / len(tempos), 1) if tempos else None, "por_origem": dict(por_origem), "por_dia": dict(sorted(por_dia.items())[-14:])}


async def diagnosticar_sistema(**_):
    h24 = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    erros = await db.system_logs.count_documents({"nivel": "error", "timestamp": {"$gte": h24}})
    erros_atuais = await db.system_logs.count_documents({"nivel": "error", "timestamp": {"$gte": ARRANQUE}})
    avisos = await db.system_logs.count_documents({"nivel": "warn", "timestamp": {"$gte": h24}})
    lentos = await db.request_metrics.count_documents({"duracao_ms": {"$gt": 1500}, "timestamp": {"$gte": h24}, "caminho": {"$not": {"$regex": "^(" + "|".join(ROTAS_IA) + ")"}}})
    reqs = await db.request_metrics.count_documents({"timestamp": {"$gte": h24}})
    pipeline = [{"$match": {"timestamp": {"$gte": h24}}}, {"$group": {"_id": "$caminho", "n": {"$sum": 1}, "p_ms": {"$avg": "$duracao_ms"}, "max_ms": {"$max": "$duracao_ms"}}}, {"$sort": {"p_ms": -1}}, {"$limit": 8}]
    rotas_lentas = [{"rota": r["_id"], "pedidos": r["n"], "media_ms": round(r["p_ms"]), "max_ms": r["max_ms"], "esperado": r["_id"].startswith(ROTAS_IA)} async for r in db.request_metrics.aggregate(pipeline)]
    aviso_por_status = {str(a["_id"]): a["n"] async for a in db.system_logs.aggregate([{"$match": {"nivel": "warn", "timestamp": {"$gte": h24}}}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    parts = await db.partners.find({}, {"_id": 0, "id": 1, "nome": 1, "status": 1, "stripe_account_id": 1, "stripe_charges_enabled": 1, "stripe_payouts_enabled": 1, "stripe_status_synced_at": 1, "currency": 1, "pix_stripe_account_id": 1, "pix_stripe_charges_enabled": 1, "pix_stripe_payouts_enabled": 1}).to_list(500)
    hoje = datetime.now(timezone.utc).date().isoformat()
    em7 = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
    camps = await db.campaigns.find({"status": "Ativa"}, {"_id": 0, "id": 1, "nome": 1, "validade": 1}).to_list(1000)
    ultimo_webhook = await db.payment_transactions.find_one({}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
    ultimo_erro = await db.system_logs.find_one({"nivel": "error"}, {"_id": 0, "timestamp": 1, "mensagem": 1}, sort=[("timestamp", -1)])
    git_ok = shutil.which("git") is not None
    return {"janela": "24h", "arranque_do_servidor": ARRANQUE,
            "saude": {"pedidos_api": reqs, "erros_500_24h": erros, "erros_500_desde_deploy_atual": erros_atuais, "erros_500": erros_atuais,
                      "nota_erros": "Existem erros anteriores ao arranque atual. A ausência de novos erros não comprova a correção; compare versões e execute testes de regressão." if erros and not erros_atuais else None,
                      "avisos_4xx": avisos, "avisos_4xx_por_status": aviso_por_status, "pedidos_lentos_1500ms": lentos, "rotas_mais_lentas": rotas_lentas,
                      "nota_lentidao": "rotas marcadas esperado=true são chamadas a modelos de IA (3-15s é normal); não são problemas de performance",
                      "ultimo_erro_500": ultimo_erro, "motor_patches": "git" if git_ok else "interno (Python, sem dependência de git — funcional)"},
            "stripe": {"modo": os.environ.get("STRIPE_MODE", "?"), "hoteis_ativos": sum(1 for p in parts if p.get("status") == "Ativo"),
                       "fonte_estado": "Base local; estes indicadores não substituem uma consulta atual ao Stripe.",
                       "hoteis_sem_connect": [p["nome"] for p in parts if p.get("status") == "Ativo" and not p.get("pix_stripe_account_id" if p.get("currency") == "brl" else "stripe_account_id")],
                       "connect_por_estabelecimento": [{"id": p["id"], "nome": p["nome"], "currency": p.get("currency", "eur"), "account_id": p.get("pix_stripe_account_id" if p.get("currency") == "brl" else "stripe_account_id"), "charges_enabled_cached": p.get("pix_stripe_charges_enabled" if p.get("currency") == "brl" else "stripe_charges_enabled"), "ultima_consulta_confirmada": p.get("stripe_status_synced_at") if p.get("currency", "eur") == "eur" else None, "fonte": "cache_local"} for p in parts],
                       "hoteis_connect_incompleto": [p["nome"] for p in parts if p.get("stripe_account_id") and p.get("stripe_charges_enabled") is False],
                       "hoteis_connect_por_verificar": [p["nome"] for p in parts if p.get("stripe_account_id") and not p.get("stripe_status_synced_at")], "ultimo_pagamento": (ultimo_webhook or {}).get("created_at")},
            "operacao": {"parceiros_pendentes": [p["nome"] for p in parts if p.get("status") == "Pendente"], "campanhas_expiradas_ainda_ativas": [c["nome"] for c in camps if (c.get("validade") or "9999") < hoje],
                         "campanhas_a_expirar_7d": [c["nome"] for c in camps if hoje <= (c.get("validade") or "9999") <= em7], "acoes_pendentes_ceo": await db.acoes_pendentes.count_documents({"status": "pendente"})}}


async def briefing() -> dict:
    diag = await diagnosticar_sistema()
    m = await metricas_granulares("campanha", 30)
    alertas = []
    s = diag["saude"]
    if s["erros_500"]:
        ult = (s.get("ultimo_erro_500") or {}).get("timestamp", "")[11:16]
        alertas.append({"nivel": "error", "titulo": f"{s['erros_500']} erro(s) 500 desde o deploy atual" + (f" · último às {ult} UTC" if ult else ""), "detalhe": (s.get("ultimo_erro_500") or {}).get("mensagem", "")[:110], "acao": "consulta os logs de erro das últimas 24h e explica a causa"})
    elif s["erros_500_24h"]:
        alertas.append({"nivel": "info", "titulo": f"{s['erros_500_24h']} erro(s) 500 da versão anterior — já corrigidos", "detalhe": "Nenhum erro desde o deploy atual", "acao": None})
    if s["pedidos_lentos_1500ms"] > 5:
        alertas.append({"nivel": "warn", "titulo": f"{s['pedidos_lentos_1500ms']} pedidos lentos (>1,5s, excluindo IA)", "detalhe": ", ".join(r["rota"] for r in s["rotas_mais_lentas"] if not r["esperado"])[:120], "acao": "diagnostica o sistema e identifica as rotas mais lentas"})
    for n in diag["stripe"]["hoteis_sem_connect"][:5]:
        alertas.append({"nivel": "warn", "titulo": f"{n} ainda não ativou o split Stripe", "detalhe": "Sem Stripe Connect as vendas não fazem split automático", "acao": f"prepara um email para o hotel {n} a pedir que ative o Stripe Connect"})
    for n in diag["stripe"]["hoteis_connect_incompleto"][:5]:
        alertas.append({"nivel": "warn", "titulo": f"{n}: verificação Stripe incompleta", "detalhe": "Onboarding iniciado mas charges ainda desativados", "acao": f"analisa a situação Stripe do hotel {n}"})
    for n in diag["operacao"]["parceiros_pendentes"][:5]:
        alertas.append({"nivel": "info", "titulo": f"Parceiro pendente de aprovação: {n}", "detalhe": "Gestão › Parceiros", "acao": None})
    for n in diag["operacao"]["campanhas_expiradas_ainda_ativas"][:5]:
        alertas.append({"nivel": "warn", "titulo": f"Campanha expirada mas ativa: {n}", "detalhe": "A validade já passou", "acao": f"analisa a campanha {n} e propõe renovar ou encerrar"})
    for n in diag["operacao"]["campanhas_a_expirar_7d"][:5]:
        alertas.append({"nivel": "info", "titulo": f"Campanha expira em 7 dias: {n}", "detalhe": "Decidir renovação", "acao": f"analisa a performance da campanha {n} e recomenda se devo renovar"})
    for c in m["itens"]:
        if c.get("status") == "Ativa" and c["alerta"] in ("cliques sem QR baixado", "QR baixados sem vendas") and c["cliques"] >= 3:
            alertas.append({"nivel": "warn", "titulo": f"Campanha {c['nome']}: {c['alerta']}", "detalhe": f"{c['cliques']} cliques · {c['qr_baixados']} QR · {c['vendas']} vendas", "acao": f"analisa porque a campanha {c['nome']} tem {c['alerta']} e propõe uma ação"})
    top = [c for c in m["itens"] if c["receita"] > 0][:3]
    return {"gerado_em": datetime.now(timezone.utc).isoformat(), "alertas": alertas[:12], "saude": s, "top_campanhas": [{k: c[k] for k in ("nome", "receita", "vendas", "conversao_pct")} for c in top], "funil_30d": m["total"]}
