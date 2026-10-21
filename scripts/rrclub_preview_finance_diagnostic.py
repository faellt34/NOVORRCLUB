#!/usr/bin/env python3
"""RRClub — diagnóstico somente leitura do banco usado pelo PREVIEW Emergent.

NÃO altera base de dados, não chama Stripe, não cria pagamentos,
não envia segredos para a saída, não faz deploy.
"""
import asyncio
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    print("ERRO: dependências motor/python-dotenv não disponíveis.")
    sys.exit(2)

load_dotenv(ROOT / "backend" / ".env")
mongo = os.environ.get("MONGO_URL", "")
database_name = os.environ.get("DB_NAME", "")
stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")

if not mongo or not database_name:
    print("ERRO: MONGO_URL/DB_NAME não definidos no backend; nada foi modificado.")
    sys.exit(2)


def as_amount(v):
    if v is None:
        return "?"
    try:
        return f"{float(v):.2f} EUR"
    except (TypeError, ValueError):
        return "(valor não numérico)"


def mode(k):
    return ("live" if k.startswith("sk_live_") else
            "test" if k.startswith("sk_test_") else
            "não identificado")


async def main():
    print("=== RRCLUB: DIAGNÓSTICO DE DADOS DO PREVIEW ===")
    print("Banco de dados:", database_name)
    print("Identificador da ligação:", hashlib.sha256(mongo.encode()).hexdigest()[:10])
    print("Configuração Stripe do backend:", mode(stripe_key))
    print("NÃO imprime credenciais, emails, IBAN, números de cartão ou dados pessoais.")
    client = AsyncIOMotorClient(mongo, serverSelectionTimeoutMS=7000)
    try:
        await client.admin.command("ping")
        db = client[database_name]
        pt_query = {
            "kind": "coupon_pay",
            "$or": [{"currency": "eur"}, {"currency": {"$exists": False}}],
        }
        count = await db.payment_transactions.count_documents(pt_query)
        samples = await db.payment_transactions.find(
            pt_query,
            {"_id": 0, "coupon": 1, "session_id": 1, "amount": 1,
             "currency": 1, "payment_status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(100).to_list(100)
        real_query = {"coupon": "RR-BBB7"}
        real_payments = await db.payment_transactions.find(
            real_query, {"_id": 0, "coupon": 1, "session_id": 1, "amount": 1,
                         "currency": 1, "kind": 1, "payment_status": 1}
        ).limit(12).to_list(12)
        real_redemptions = await db.redemptions.count_documents(real_query)
        fake_count = await db.payment_transactions.count_documents(
            {"kind": "coupon_pay", "coupon": "CLUB-10"}
        )

        print("Transações de cupão listáveis como Portugal:", count)
        print("Registos com cupão CLUB-10:", fake_count)
        print("Transações RR-BBB7 neste banco:", len(real_payments))
        print("Redenções RR-BBB7 neste banco:", real_redemptions)
        print("Das primeiras 100 transações EUR:")
        print("  Checkout live:", sum(str(t.get("session_id") or "").startswith("cs_live_") for t in samples))
        print("  Checkout test:", sum(str(t.get("session_id") or "").startswith("cs_test_") for t in samples))
        print("  Outro/sem sessão:", sum(not str(t.get("session_id") or "").startswith(("cs_live_", "cs_test_")) for t in samples))
        print("  Coupões mostrados (máximo 8):", ", ".join(sorted(set(str(t.get("coupon", "?")) for t in samples))[:8]))

        for t in real_payments:
            sid = str(t.get("session_id") or "")
            session_type = ("live" if sid.startswith("cs_live_") else
                            "test" if sid.startswith("cs_test_") else "outro/ausente")
            print(
                "RR-BBB7 | valor:", as_amount(t.get("amount")),
                "| estado local:", t.get("payment_status") or "ausente",
                "| checkout:", session_type,
                "| moeda:", t.get("currency") or "sem moeda",
                "| tipo:", t.get("kind") or "sem tipo",
            )

        if not real_payments:
            print("CONCLUSÃO: RR-BBB7 não consta das transações deste banco.")
            print("Pode tratar-se de uma base de pré-visualização isolada ou de dados ainda não importados.")
            print("NÃO copiar nem criar registos financeiros para simular o pagamento.")
        else:
            print("CONCLUSÃO: existe um registo local RR-BBB7; ainda é necessário comparar as provas Stripe.")
        print("DIAGNÓSTICO CONCLUÍDO — 0 escritas / 0 chamadas Stripe / 0 deploy.")
    finally:
        client.close()

try:
    asyncio.run(main())
except Exception as e:
    print("ERRO: ligação de leitura ao banco falhou:", type(e).__name__)
    sys.exit(1)
