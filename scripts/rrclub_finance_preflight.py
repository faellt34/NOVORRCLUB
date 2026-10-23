#!/usr/bin/env python3
"""RRClub: auditoria financeira P5 somente leitura (PT e BR).

NÃO cria cobranças, links, transferências, payouts, contas, nem altera metadata.
Executar na raiz: python3 scripts/rrclub_finance_preflight.py
"""
import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")
import stripe
from core import db

RULES = {
    "PT": ("STRIPE_SECRET_KEY", "stripe_account_id"),
    "BR": ("PIX_STRIPE_SECRET_KEY", "pix_stripe_account_id"),
}


async def internal_links(field):
    docs = []
    projection = {"_id": 0, "id": 1, "nome": 1, "currency": 1, field: 1}
    for collection, role in ((db.partners, "partner"), (db.influencers, "influencer")):
        for obj in await collection.find({field: {"$exists": True, "$ne": ""}}, projection).to_list(length=2000):
            account_id = obj.get(field)
            if isinstance(account_id, str) and account_id.startswith("acct_"):
                docs.append((account_id, role, str(obj.get("id") or ""), str(obj.get("nome") or "Sem nome")))
    index = defaultdict(list)
    for account_id, role, entity_id, name in docs:
        index[account_id].append((role, entity_id, name))
    return index


async def main():
    print("=== RRCLUB | PRÉ-VALIDAÇÃO FINANCEIRA SOMENTE LEITURA ===")
    print("NÃO foram criadas cobranças nem transferências.")
    for country, (key_name, field) in RULES.items():
        key = os.getenv(key_name, "")
        print("\n" + country + ":")
        if not key.startswith(("sk_live_", "rk_live_", "sk_test_", "rk_test_")):
            print("  Chave ausente ou não reconhecida; verificação interrompida.")
            continue
        mode = "LIVE" if "_live_" in key else "TEST"
        print("  Modo Stripe:", mode)
        if country == "PT":
            for flag in ("P5_ENABLED", "P5_EUR_ENABLED", "PT_SPLIT_ENABLED",
                         "PT_SPLIT_LIVE_ENABLED", "PT_SPLIT_AUTO_TRANSFER"):
                print("  " + flag + ":", os.getenv(flag, "false").lower() == "true")
        else:
            for flag in ("P5_ENABLED", "P5_BRL_ENABLED", "PIX_ENABLED"):
                print("  " + flag + ":", os.getenv(flag, "false").lower() == "true")
            print("  Configuração Pix definida:", bool(os.getenv("PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION")))
            print("  Webhook Pix definido:", bool(os.getenv("PIX_STRIPE_WEBHOOK_SECRET")))
        try:
            remote = await asyncio.to_thread(stripe.Account.list, api_key=key, limit=100)
            accounts = list(remote.get("data") or [])
            links = await internal_links(field)
        except Exception as exc:
            print("  Falha de leitura:", type(exc).__name__)
            continue
        print("  Contas Connect consultadas:", len(accounts))
        if remote.get("has_more"):
            print("  ATENÇÃO: mais de 100 contas; inventário incompleto")
        complete = 0
        ready = 0
        for account in accounts:
            aid = account.get("id", "")
            owners = links.get(aid, [])
            metadata = account.get("metadata") or {}
            # Consultar o objeto individual quando existe um vínculo no banco;
            # a listagem isolada nunca é prova suficiente de titularidade.
            if owners:
                try:
                    detail = await asyncio.to_thread(stripe.Account.retrieve, aid, api_key=key)
                    metadata = detail.get("metadata") or {}
                except Exception:
                    metadata = {}
            transfer = (account.get("capabilities") or {}).get("transfers") == "active"
            receiving = transfer and account.get("payouts_enabled") is True
            ready += int(receiving)
            verified = False
            association = "SEM VÍNCULO"
            if len(owners) > 1:
                association = "DUPLICADO NO CADASTRO"
            elif len(owners) == 1:
                role, entity_id, name = owners[0]
                exact = metadata.get(role + "_id") == entity_id
                if country == "BR" and role == "influencer" and not metadata.get("influencer_id"):
                    exact = metadata.get("partner_id") == entity_id
                verified = bool(exact)
                association = ("ID CONFIRMADO" if exact else "METADATA PENDENTE")
                association += " | " + role + " | " + name[:28]
            complete += int(receiving and verified)
            print("  acct_…" + aid[-6:] + " | " +
                  ("RECEBE" if receiving else "PENDENTE") + " | " + association)
        missing = [x for x in links if x not in {a.get("id") for a in accounts}]
        print("  Contas referenciadas no banco mas ausentes nesta Stripe:", len(missing))
        print("  Com transferências/recebimentos habilitados:", ready)
        print("  Habilitadas E com ID comprovado:", complete)
        print("  Estado:", "PRONTO PARA AUDITORIA DE CAMPANHA" if complete else "SEM BENEFICIÁRIOS COMPROVADOS")
    print("\nConcluído. Nenhum dado financeiro foi modificado.")


if __name__ == "__main__":
    asyncio.run(main())
