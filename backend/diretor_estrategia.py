"""Diretor IA 2.0: leitura executiva verificável, sem chamadas IA ou escrita financeira.

Valores vêm de payment_transactions (webhook local), não de resgates manuais.
Não equivale a confirmação bancária ou a consulta live à Stripe.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from core import db, NO_ID
from payment_policy import currency_query


TEAM = [
    {"id": "diretor", "nome": "Diretor Executivo", "funcao": "priorizar decisões fundamentadas"},
    {"id": "p5", "nome": "Operações P5", "funcao": "funil QR, scan, checkout e cobrança"},
    {"id": "br", "nome": "Finanças Brasil", "funcao": "Pix, BRL, Connect e conciliação"},
    {"id": "pt", "nome": "Finanças Portugal", "funcao": "MB WAY/cartão, EUR e conciliação"},
    {"id": "marketing", "nome": "Marketing e Crescimento", "funcao": "conversão, campanhas e oportunidade local"},
    {"id": "pesquisa", "nome": "Pesquisa de Mercado", "funcao": "pesquisar oportunidades apenas com fontes atuais citáveis"},
    {"id": "engenharia", "nome": "Engenharia e Segurança", "funcao": "logs, testes e propostas de correção aprovadas"},
]


def is_synthetic(record):
    """Exclui simulações explícitas; dados legados incertos não viram pagamento real."""
    return bool(
        record.get("is_test") or record.get("test_run_id") or record.get("livemode") is False
        or str(record.get("origem") or "").lower() in ("teste", "test", "simulacao", "simulação")
        or "simulação" in str(record.get("staff") or "").lower()
        or str(record.get("idempotency_key") or "").startswith("test-")
    )


def is_new_p5(record, currency):
    """P5 real tem vínculo, versão e moeda explícitos; coupon_pay antigo não é P5."""
    if record.get("currency") != currency or is_synthetic(record):
        return False
    if currency == "brl":
        return record.get("kind") == "pix_coupon" and record.get("split_version") == "br-fixed-5-80-5-10-v1"
    return bool(
        record.get("kind") == "coupon_pay"
        and record.get("p5_charge_id") and record.get("split_version") == "pt-p5-fixed-5-80-5-10-v1"
        and record.get("gross_minor") is not None
    )


def money_minor(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value))
        return int(d) if d.is_finite() and d >= 0 and d == d.to_integral_value() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def amounts_minor(tx, currency):
    """Usa snapshot da cobrança; nunca deriva valores fictícios ou impostos."""
    if currency == "brl":
        parts = ("gross_cents", "net_cents", "partner_cents", "influencer_cents", "platform_cents")
    else:
        parts = ("gross_minor", "partner_minor", "influencer_minor", "platform_minor")
    vals = {k: money_minor(tx.get(k)) for k in parts}
    if any(x is None for x in vals.values()):
        return None
    if currency == "brl":
        gross, net, partner, influence, platform = (vals[k] for k in parts)
    else:
        gross, partner, influence, platform = (vals[k] for k in parts)
        net = gross - (gross * 5 // 100)
        # Valores em EUR devem coincidir com a cobrança Stripe registada.
        charge = tx.get("amount")
        if charge is None:
            return None
        try:
            net = int((Decimal(str(charge)) * 100).quantize(Decimal("1")))
        except (InvalidOperation, TypeError, ValueError):
            return None
    if not (gross > 0 and net >= 0 and partner + influence + platform == net):
        return None
    return {"bruto": gross, "cobrado": net, "parceiro": partner, "influenciador": influence, "rrclub": platform}


def financial_state(tx, currency):
    """Classificação conservadora para relato, sem emitir transferências."""
    if not is_new_p5(tx, currency):
        return "fora_p5"
    if is_synthetic(tx):
        return "simulacao"
    if tx.get("dispute_hold") or tx.get("dispute_id"):
        return "em_disputa"
    if tx.get("refunded_cents") or tx.get("refunded_amount") or tx.get("refunded"):
        return "reembolso_a_conciliar"
    if tx.get("payment_status") != "paid":
        return "aguarda_pagamento"
    if amounts_minor(tx, currency) is None:
        return "valor_incompleto"
    if currency == "brl":
        transferred = (
            tx.get("split_status") == "completed"
            and tx.get("partner_transfer_id") and tx.get("influencer_transfer_id")
        )
    else:
        transferred = (
            tx.get("pt_split_status") == "transferred_to_connect"
            and tx.get("partner_transfer_id") and tx.get("influencer_transfer_id")
        )
    return "transferido_connect" if transferred else "pago_repasses_pendentes"


def euros_or_reais(cents):
    return round(cents / 100, 2)


async def snapshot_currency(currency, days=30):
    if currency not in ("eur", "brl"):
        raise ValueError("Moeda inválida")
    days = max(1, min(int(days), 90))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q = {"currency": currency, "created_at": {"$gte": cutoff}}
    transactions = await db.payment_transactions.find(q, NO_ID).to_list(20000)
    p5 = [tx for tx in transactions if is_new_p5(tx, currency)]
    states = {}
    sums = {key: 0 for key in ("bruto", "cobrado", "parceiro", "influenciador", "rrclub")}
    campaigns = {}
    for tx in p5:
        state = financial_state(tx, currency)
        states[state] = states.get(state, 0) + 1
        if state not in ("transferido_connect", "pago_repasses_pendentes"):
            continue
        amounts = amounts_minor(tx, currency)
        for k in sums:
            sums[k] += amounts[k]
        cid = tx.get("campaign_id") or "(sem id)"
        item = campaigns.setdefault(cid, {"id": cid, "nome": tx.get("campaign") or "Campanha", "pagamentos_p5": 0, "cobrado": 0})
        item["pagamentos_p5"] += 1
        item["cobrado"] += amounts["cobrado"]

    click_q = currency_query({"date": {"$gte": cutoff}}, currency)
    claims = await db.coupon_claims.find(click_q, {"_id": 0, "is_test": 1, "test_run_id": 1, "origem": 1, "idempotency_key": 1}).to_list(20000)
    clicks = sum(not is_synthetic(x) for x in claims)
    p5_sessions = await db.p5_sessions.find(
        {"currency": currency, "created_at": {"$gte": cutoff}},
        {"_id": 0, "scanned_at": 1, "is_test": 1, "test_run_id": 1}
    ).to_list(20000)
    scanned = sum(bool(x.get("scanned_at")) for x in p5_sessions if not is_synthetic(x))
    charges = await db.p5_charges.find(
        {"currency": currency, "created_at": {"$gte": cutoff}},
        {"_id": 0, "status": 1, "checkout_url": 1, "is_test": 1, "test_run_id": 1}
    ).to_list(20000)
    prepared = [c for c in charges if not is_synthetic(c)]
    checkout_count = sum(bool(c.get("checkout_url") or c.get("status") in ("checkout", "paid")) for c in prepared)
    result = {
        "currency": currency, "periodo_dias": days, "fonte": "base_local.payment_transactions + registos QR/P5",
        "interpretacao": "Confirmado no registo local pós-webhook; não é extrato Stripe nem crédito no IBAN.",
        "vendas_p5_pagas": sum(states.get(x, 0) for x in ("transferido_connect", "pago_repasses_pendentes")),
        "financeiro": {key: euros_or_reais(value) for key, value in sums.items()},
        "repasses_connect_confirmados": states.get("transferido_connect", 0),
        "pagos_com_repasses_pendentes": states.get("pago_repasses_pendentes", 0),
        "depositos_bancarios_confirmados": None,
        "tarifas_stripe_efetivas": None,
        "iva": None,
        "pagamentos_legados_ou_nao_p5": sum(
            tx.get("payment_status") == "paid" and not is_synthetic(tx)
            for tx in transactions if not is_new_p5(tx, currency)
        ),
        "estados_p5": states,
        "funil_observado": {
            "aberturas_cupom": clicks,
            "sessoes_p5": len(p5_sessions),
            "scans_p5": scanned,
            "checkouts_p5": checkout_count,
            "pagamentos_p5": sum(states.get(x, 0) for x in ("transferido_connect", "pago_repasses_pendentes")),
            "repasses_connect": states.get("transferido_connect", 0),
        },
        "campanhas_com_pagamento": sorted(
            ({**v, "cobrado": euros_or_reais(v["cobrado"])} for v in campaigns.values()),
            key=lambda x: -x["cobrado"],
        )[:10],
    }
    return result


async def resumo_estrategico(days=30):
    br, pt = await snapshot_currency("brl", days), await snapshot_currency("eur", days)
    alertas, propostas = [], []
    for item in (br, pt):
        cur = item["currency"].upper()
        if item["pagos_com_repasses_pendentes"]:
            alertas.append({
                "severidade": "atencao", "titulo": f"{cur}: repasse a conciliar",
                "evidencia": f"{item['pagos_com_repasses_pendentes']} pagamentos P5 locais pagos sem ambos os IDs de transferência",
                "acao": "Verificar exclusivamente as transações afetadas na Stripe, sem repetir repasses",
            })
        if item["pagamentos_legados_ou_nao_p5"]:
            alertas.append({
                "severidade": "informativo", "titulo": f"{cur}: pagamentos fora do P5",
                "evidencia": f"{item['pagamentos_legados_ou_nao_p5']} pagamentos registados fora do novo P5",
                "acao": "Reconciliar o fluxo antigo separadamente; nunca contabilizar como split P5",
            })
        if item["funil_observado"]["aberturas_cupom"] and not item["vendas_p5_pagas"]:
            propostas.append({
                "prioridade": "media", "especialista": "marketing",
                "titulo": f"{cur}: avaliar conversão da campanha",
                "evidencia": f"{item['funil_observado']['aberturas_cupom']} aberturas registadas e nenhum P5 pago verificável no período",
                "acao": "Rever QR, scan e checkout com um parceiro apto; propor campanha apenas após avaliação",
                "aprovacao_necessaria": True,
            })
    if not propostas:
        propostas.append({
            "prioridade": "media", "especialista": "diretor",
            "titulo": "Acompanhar o piloto por país",
            "evidencia": "Métricas locais segregadas em EUR e BRL; não há previsão de faturação confiável sem série real",
            "acao": "Comparar funil, pagamentos e repasses de cada campanha nos próximos testes",
            "aprovacao_necessaria": False,
        })
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "modo": "somente_leitura_sem_custo_llm",
        "equipa": TEAM,
        "financeiro_por_pais": {"brl": br, "eur": pt},
        "alertas": alertas[:5],
        "decisoes_prioritarias": propostas[:3],
        "regras": {
            "desconto": "5% do valor bruto (não é automaticamente 5 unidades monetárias em qualquer compra)",
            "split_do_bruto": {"parceiro": 80, "influenciador": 5, "rrclub": 10, "desconto_seguidor": 5},
            "taxas_stripe_e_tributos": "não calculados sem prova documental",
            "verificacao_connect_individual": "não significa indisponibilidade de toda a RRClub",
            "aprovacao": "nenhuma ação financeira executada por esta funcionalidade",
        },
    }
