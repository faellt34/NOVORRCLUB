"""Reconciliação BR RRClub: metadados Connect, sem cobrança/transferência.

Dry-run por defeito. Aplicação requer --apply --confirm-db NOME_EXATO.
Nunca cria contas, muda IBAN, altera MongoDB ou produz pagamentos.
"""
import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EXPECTED = (
    {"role": "partner", "collection": "partners", "internal_id": "p-fc194b8f5c",
     "stripe_id": "acct_1URwhrCiKOcSLJUr", "metadata_key": "partner_id"},
    {"role": "influencer", "collection": "influencers", "internal_id": "if-da6af205f9",
     "stripe_id": "acct_1URxAICihW3I0NpA", "metadata_key": "influencer_id"},
)


def check_local(record, expected):
    if not record or record.get("id") != expected["internal_id"]:
        return "cadastro_interno_nao_encontrado"
    if record.get("pix_stripe_account_id") != expected["stripe_id"]:
        return "ligacao_producao_diferente_ou_ausente"
    if record.get("currency") not in (None, "brl"):
        return "moeda_interna_incompativel"
    if record.get("status") in ("Pendente", "Suspenso"):
        return "cadastro_interno_pendente"
    return None


def check_stripe(account, expected):
    if account.get("id") != expected["stripe_id"] or account.get("country") != "BR":
        return "conta_stripe_diferente_ou_pais_incorreto"
    meta = account.get("metadata") or {}
    key = expected["metadata_key"]
    opposite = "influencer_id" if key == "partner_id" else "partner_id"
    if meta.get(key) not in (None, "", expected["internal_id"]):
        return "conflito_de_titularidade"
    if meta.get(opposite) and meta.get(opposite) != expected["internal_id"]:
        return "conta_ja_associada_a_outro_papel"
    if (account.get("capabilities") or {}).get("transfers") != "active":
        return "transferencias_nao_ativas"
    if account.get("payouts_enabled") is not True:
        return "depositos_nao_habilitados"
    interval = (((account.get("settings") or {}).get("payouts") or {}).get("schedule") or {}).get("interval")
    if interval != "daily":
        return "deposito_automatico_nao_diario"
    return None


async def run():
    parser = argparse.ArgumentParser(description="RRClub: leitura e reconciliação segura de metadados Connect BR")
    parser.add_argument("--apply", action="store_true", help="Aplicar metadados apenas se todas as verificações passarem")
    parser.add_argument("--confirm-db", default="", help="Nome exato da base de produção observado no dry-run")
    args = parser.parse_args()

    from core import db, NO_ID
    from routes_pix import pix_key
    import stripe

    name = db.name
    if args.apply and (not args.confirm_db or args.confirm_db != name
                       or "test" in name.lower() or "dev" in name.lower()):
        raise SystemExit("BLOQUEADO: base de produção não confirmada; não houve alterações.")
    if EXPECTED[0]["stripe_id"] == EXPECTED[1]["stripe_id"]:
        raise SystemExit("BLOQUEADO: destinatários duplicados.")
    key = pix_key()
    validations = []
    for expected in EXPECTED:
        collection = getattr(db, expected["collection"])
        local = await collection.find_one({"id": expected["internal_id"]}, NO_ID)
        account = await asyncio.to_thread(
            stripe.Account.retrieve, expected["stripe_id"], api_key=key
        )
        issue = check_local(local, expected) or check_stripe(account, expected)
        existing = (account.get("metadata") or {}).get(expected["metadata_key"])
        validations.append((expected, issue, existing))
        print(f"{expected['role']} {expected['internal_id']} ↔ {expected['stripe_id']}: "
              f"{'BLOQUEADO '+issue if issue else 'associação apta'}; "
              f"metadata_atual={'conferido' if existing == expected['internal_id'] else 'ausente'}")

    if any(issue for _, issue, _ in validations):
        raise SystemExit("Nenhum metadado alterado. Verificar exclusivamente as associações bloqueadas.")
    if not args.apply:
        print(f"DRY-RUN OK. Base observada: {name}. Para aplicar explicitamente: "
              f"--apply --confirm-db {name}")
        return

    for expected, _, existing in validations:
        if existing == expected["internal_id"]:
            continue
        await asyncio.to_thread(
            stripe.Account.modify, expected["stripe_id"],
            metadata={expected["metadata_key"]: expected["internal_id"]},
            api_key=key,
        )
        verify = await asyncio.to_thread(
            stripe.Account.retrieve, expected["stripe_id"], api_key=key
        )
        if (verify.get("metadata") or {}).get(expected["metadata_key"]) != expected["internal_id"]:
            raise SystemExit("Falha de verificação Stripe; parar e reconciliar manualmente.")
        print(f"CONFIRMADO: metadado {expected['metadata_key']} guardado em {expected['stripe_id']}.")
    print("Finalizado: sem pagamentos, sem transferências, sem duplicados.")


if __name__ == "__main__":
    asyncio.run(run())
