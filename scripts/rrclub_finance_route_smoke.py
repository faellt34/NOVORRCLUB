#!/usr/bin/env python3
"""RRClub - prova local read-only da rota que o botão Verificar na Stripe usa.

Não requer login, não lê registos reais da base, não altera bases de dados,
não chama Stripe, não executa pagamento/transferência/deploy.
O teste simula uma única consulta para verificar a integração técnica.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
if not (BACKEND / "server.py").is_file():
    raise SystemExit("PARADO: execute no projeto RRClub (/app).")
if not (BACKEND / "routes_pix.py").is_file():
    raise SystemExit("PARADO: código Pix Brasil não encontrado.")

sys.path.insert(0, str(BACKEND))
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
    import stripe
    import routes_finance
    from server import app
    from fastapi import HTTPException
    from finance_evidence import transfer_evidence, charge_cost_evidence
except Exception as exc:
    raise SystemExit("PARADO: erro ao importar o backend: "
                     + type(exc).__name__ + ": " + str(exc)[:250])

print("RRCLUB - TESTE RÁPIDO DA AUDITORIA FINANCEIRA", flush=True)
print("Modo: SIMULAÇÃO LOCAL, sem transações reais.", flush=True)

# O GET do botão tem de ser registado e protegido por role=admin.
wanted = {
    "/api/admin/finance/reconciliation",
    "/api/admin/finance/reconciliation/{session_id}",
}
routes = {}
for route in app.routes:
    if getattr(route, "path", "") in wanted:
        routes[route.path] = route

if set(routes) != wanted:
    raise SystemExit("FALHA: falta rota admin de auditoria no servidor.")
for path, route in routes.items():
    if set(getattr(route, "methods", [])) != {"GET"}:
        raise SystemExit("FALHA: rota financeira não é GET-only: " + path)
    dependencies = list(getattr(route, "dependant", SimpleNamespace(dependencies=[])).dependencies)
    admins = []
    for dep in dependencies:
        call = getattr(dep, "call", None)
        for cell in (getattr(call, "__closure__", ()) or ()):
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if isinstance(value, tuple) and value == ("admin",):
                admins.append(True)
    if not admins:
        raise SystemExit("FALHA: rota admin sem proteção de função admin: " + path)
print("APROVADO: endpoints GET registados e protegidos por admin.", flush=True)

component = FRONTEND / "src/components/FinanceReconciliationPanel.jsx"
page = FRONTEND / "src/pages/AdminPayouts.jsx"
if not component.is_file() or not page.is_file():
    raise SystemExit("FALHA: componente e página de auditoria não encontrados.")
jsx, payouts = component.read_text(), page.read_text()
required = [
    'api.get("/admin/finance/reconciliation")',
    '"/admin/finance/reconciliation/"',
    'encodeURIComponent(row.session_id)',
    'Verificar na Stripe',
]
if not all(piece in jsx for piece in required):
    raise SystemExit("FALHA: ligação do botão à rota financeira incompleta.")
if "FinanceReconciliationPanel" not in payouts:
    raise SystemExit("FALHA: componente de auditoria não está incluído nos Pagamentos.")
if "reportCurrency()" not in payouts:
    raise SystemExit("FALHA: isolamento de moeda EUR/BRL não confirmado.")
print("APROVADO: botão ligado à rota; interface Portugal e Pix isoladas.", flush=True)

# Exercitar a função REAL do endpoint, substituindo apenas as fontes de dados
# POR MÓCKS EM MEMÓRIA neste processo de teste.
fixture = {
    "kind": "coupon_pay", "session_id": "cs_unit_smoke",
    "payment_status": "pending", "campaign_id": "campaign_unit",
    "partner_id": "partner_unit", "coupon": "COUPON-UNIT",
    "amount": 2.0, "currency": "eur",
}
partner = {"id": "partner_unit", "stripe_account_id": "acct_unit"}
redemption = {
    "idempotency_key": "cs_unit_smoke",
    "coupon": fixture["coupon"],
    "campaign_id": fixture["campaign_id"],
    "partner_id": fixture["partner_id"],
    "commission": 0.10,
    "currency": "eur",
}

class FakeCollection:
    def __init__(self, obj):
        self.obj = obj
    async def find_one(self, query, projection=None):
        if self.obj is fixture:
            return self.obj if query.get("session_id") == fixture["session_id"] else None
        if self.obj is redemption:
            return self.obj if query.get("idempotency_key") == fixture["session_id"] else None
        return self.obj

fake_db = SimpleNamespace(
    payment_transactions=FakeCollection(fixture),
    partners=FakeCollection(partner),
    redemptions=FakeCollection(redemption),
)

original_db = routes_finance.db
original_stripe_evidence = routes_finance._stripe_evidence
called = []

def fake_stripe_evidence(session_id, intent_id, amount, destination, expected, commission_minor):
    called.append(True)
    assert session_id == fixture["session_id"]
    assert amount == 200
    assert destination == "acct_unit"
    assert expected["campaign_id"] == "campaign_unit"
    assert commission_minor == 10
    return {
        "state": "no_transfer_evidence",
        "stripe_session_paid": True,
        "fee_verified": True,
        "stripe_gross_minor": 200,
        "stripe_fee_minor": 30,
        "stripe_net_minor": 170,
        "commission_minor": 10,
        "fee_exceeds_commission": True,
        "bank_payout": "not_verified",
    }

async def test():
    try:
        routes_finance.db = fake_db
        routes_finance._stripe_evidence = fake_stripe_evidence
        result = await routes_finance.reconciliation_detail(
            fixture["session_id"], user={"id": "admin_unit", "role": "admin"}
        )
        assert called
        assert result["state"] == "no_transfer_evidence"
        assert result["stripe_session_paid"] is True
        assert result["ledger_discrepancy"] is True
        assert result["local_payment_status"] == "pending"
        assert result["bank_payout"] == "not_verified"
        assert result["fee_exceeds_commission"] is True
        fixture["payment_status"] = "paid"
        settled = await routes_finance.reconciliation_detail(
            fixture["session_id"], user={"id": "admin_unit", "role": "admin"}
        )
        assert settled["ledger_discrepancy"] is False
        try:
            await routes_finance.reconciliation_detail(
                "cs_untracked", user={"id": "admin_unit", "role": "admin"}
            )
            raise AssertionError("Ausência de transação não devolveu 404")
        except HTTPException as e:
            assert e.status_code == 404
    finally:
        routes_finance.db = original_db
        routes_finance._stripe_evidence = original_stripe_evidence

try:
    asyncio.run(test())
    bad = transfer_evidence(
        {"status": "succeeded", "amount": 200, "currency": "eur"},
        None, None, 200, "acct_unit"
    )
    assert bad["state"] == "no_transfer_evidence"
    assert bad["bank_payout"] == "not_verified"
    fee = charge_cost_evidence(
        {"amount": 200, "fee": 30, "net": 170, "currency": "eur"}, 200, 10
    )
    assert fee["fee_verified"] and fee["fee_exceeds_commission"]
    print("APROVADO: botão -> endpoint -> resultado, incluindo webhook atrasado.", flush=True)
    print("APROVADO: comissão não prova transferência nem payout bancário.", flush=True)
    print("APROVADO: estado inexistente devolve 404.", flush=True)
    print("FIM: código funcional na simulação local; NENHUM DADO REAL ACEDIDO.", flush=True)
    print("Ainda falta validar autenticação real e consulta à Stripe na pré-visualização.", flush=True)
except Exception as exc:
    raise SystemExit("FALHA NO TESTE: " + type(exc).__name__ + ": " + str(exc)[:250])
