"""Copiloto do parceiro RRClub: insights P5 privados, verificáveis e sem custo LLM."""
from datetime import datetime, timedelta, timezone

from core import db, NO_ID
from payment_policy import currency_query
from diretor_estrategia import is_new_p5, financial_state, amounts_minor, is_synthetic


def summarize_partner_transactions(transactions, partner_id, currency):
    """Ignora dados de outro parceiro, testes, histórico e cobranças incertas."""
    paid, awaiting, held = [], 0, 0
    for tx in transactions:
        if tx.get("partner_id") != partner_id or not is_new_p5(tx, currency):
            continue
        state = financial_state(tx, currency)
        if state in ("transferido_connect", "pago_repasses_pendentes"):
            paid.append((tx, amounts_minor(tx, currency)))
            if state == "pago_repasses_pendentes":
                awaiting += 1
        elif state in ("em_disputa", "reembolso_a_conciliar", "valor_incompleto"):
            held += 1
    totals = {k: sum(parts[k] for _, parts in paid) for k in ("bruto", "cobrado", "parceiro", "influenciador", "rrclub")}
    by_campaign = {}
    for tx, parts in paid:
        cid = str(tx.get("campaign_id") or "sem_campanha")
        item = by_campaign.setdefault(cid, {
            "campaign_id": cid, "nome": str(tx.get("campaign") or "Campanha")[:100],
            "vendas_p5_pagas": 0, "cobrado_minor": 0,
        })
        item["vendas_p5_pagas"] += 1
        item["cobrado_minor"] += parts["cobrado"]
    campaigns = sorted(by_campaign.values(), key=lambda x: (-x["cobrado_minor"], x["nome"]))
    for item in campaigns:
        item["cobrado"] = round(item.pop("cobrado_minor") / 100, 2)
    count = len(paid)
    return {
        "pagamentos_p5": count, "transferencias_pendentes": awaiting, "em_disputa_ou_por_conciliar": held,
        "valores": {k: round(v / 100, 2) for k, v in totals.items()},
        "ticket_medio_cobrado": round(totals["cobrado"] / count / 100, 2) if count else None,
        "campanhas": campaigns[:8],
    }


def growth_suggestions(report, clicks, scans):
    """Recomendações proporcionais à evidência — sem projeções inventadas."""
    suggestions = []
    paid = report["pagamentos_p5"]
    if report["transferencias_pendentes"]:
        suggestions.append({
            "titulo": "Conciliar repasses pendentes",
            "motivo": f"{report['transferencias_pendentes']} pagamento(s) registado(s) como pago(s) sem dois repasses Connect confirmados",
            "passo": "Verificar o estado da sua conta Connect e contactar o administrador; não repetir transferências.",
        })
    if (clicks or scans) and not paid:
        suggestions.append({
            "titulo": "Verificar a passagem do QR até à cobrança",
            "motivo": f"{clicks} abertura(s) e {scans} scan(s), sem pagamento P5 confirmado no mesmo período",
            "passo": "Testar o checkout com o parceiro e o seguidor; verificar se os dois beneficiários estão aptos.",
        })
    if paid and report["campanhas"]:
        first = report["campanhas"][0]
        suggestions.append({
            "titulo": "Reforçar campanha com pagamentos",
            "motivo": f"{first['nome']}: {first['vendas_p5_pagas']} pagamento(s) confirmado(s) localmente",
            "passo": "Comparar cliques e resultados com outras campanhas antes de aumentar investimento.",
        })
    if paid < 3:
        suggestions.append({
            "titulo": "Recolher amostra antes de prever faturação",
            "motivo": f"Apenas {paid} pagamento(s) P5 verificável(is) neste período",
            "passo": "Continuar o piloto e medir os próximos pagamentos; não estimar ROI sem custos operacionais reais.",
        })
    return suggestions[:3]


async def partner_growth_report(partner, days=30):
    pid = partner["id"]
    currency = str(partner.get("currency") or "eur").lower()
    if currency not in ("eur", "brl"):
        raise ValueError("Moeda de parceiro inválida")
    days = max(1, min(int(days), 90))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    txs = await db.payment_transactions.find(
        {"partner_id": pid, "currency": currency, "created_at": {"$gte": cutoff}}, NO_ID
    ).to_list(20000)
    report = summarize_partner_transactions(txs, pid, currency)
    clicks_q = currency_query({"partner_id": pid, "date": {"$gte": cutoff}}, currency)
    claims = await db.coupon_claims.find(
        clicks_q, {"_id": 0, "is_test": 1, "test_run_id": 1, "origem": 1, "idempotency_key": 1}
    ).to_list(20000)
    clicks = sum(not is_synthetic(c) for c in claims)
    sessions = await db.p5_sessions.find(
        {"partner_id": pid, "currency": currency, "created_at": {"$gte": cutoff}},
        {"_id": 0, "scanned_at": 1, "is_test": 1, "test_run_id": 1}
    ).to_list(20000)
    scans = sum(bool(s.get("scanned_at")) for s in sessions if not is_synthetic(s))
    return {
        "currency": currency, "periodo_dias": days,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "fonte": "registos locais verificados; sem consulta Stripe ao vivo",
        "parceiro": {"nome": partner.get("nome"), "id": pid},
        "cliques_registados": clicks, "scans_p5": scans,
        **report,
        "sugestoes": growth_suggestions(report, clicks, scans),
        "avisos": [
            "Pagamentos confirmados no livro local pós-webhook; depósito bancário não verificado.",
            "O histórico de resgates manuais pode incluir simulações e não integra estes totais.",
            "Ticket médio cobrado não é lucro e não desconta taxas Stripe ou custos do estabelecimento.",
        ],
    }
