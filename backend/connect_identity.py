"""RRClub Connect account ownership: bank/email are not recipient identifiers.

A Stripe Connect acct_ ID may only be linked to a verified, distinct RRClub
partner or influencer. Never auto-associate accounts by email or IBAN.
"""
import os
import re

import stripe

ACCOUNT_FIELDS = ("stripe_account_id_br", "stripe_account_id_pt", "stripe_account_id")


class ConnectOwnershipError(ValueError):
    pass


def verify_account_owner(account, country, owner_kind, owner_id):
    """Strict identity matching: fail closed for missing Stripe metadata."""
    if account.get("country") != country:
        raise ConnectOwnershipError("Conta Stripe de país diferente da operação")
    metadata = account.get("metadata") or {}
    owner_type = metadata.get("rrclub_owner_type")
    stored_id = metadata.get("rrclub_owner_id")
    # Compatibility with older onboarding where ownership was stored as partner_id.
    legacy = metadata.get("partner_id") if owner_kind == "parceiros" else metadata.get("influencer_id")
    if not ((owner_type == owner_kind and stored_id == owner_id) or legacy == owner_id):
        raise ConnectOwnershipError(
            "Conta sem prova de vínculo com este parceiro/influenciador. "
            "É necessário concluir ou reconciliar o onboarding, não usar email/IBAN.")
    if not account.get("payouts_enabled"):
        raise ConnectOwnershipError("Conta Stripe ainda não está apta a receber repasses")
    if (account.get("capabilities") or {}).get("transfers") != "active":
        raise ConnectOwnershipError("Capacidade de transferências ainda não está ativa")


async def validate_new_connect_link(db, kind, owner_id, country, account_id):
    if kind not in ("parceiros", "influencers") or country not in ("BR", "PT"):
        raise ConnectOwnershipError("Tipo de participante ou país inválido")
    if not re.fullmatch(r"acct_[A-Za-z0-9]+", account_id or ""):
        raise ConnectOwnershipError("ID de conta Stripe inválido")
    # A Connect account cannot serve two different RRClub participants, even if
    # those participants share a business email or payout bank.
    q = {"$or": [{field: account_id} for field in ACCOUNT_FIELDS]}
    for collection_name in ("partners", "influencers"):
        hit = await db[collection_name].find_one(q, {"_id": 0, "id": 1})
        if hit and not (collection_name == ("partners" if kind == "parceiros" else "influencers") and hit["id"] == owner_id):
            raise ConnectOwnershipError("Conta Stripe já vinculada a outro participante RRClub")
    key = os.environ.get("STRIPE_SECRET_KEY_" + country, "")
    if not key.startswith(("sk_test_", "sk_live_")):
        raise ConnectOwnershipError("Chave Stripe do país ainda não configurada")
    try:
        account = stripe.Account.retrieve(account_id, api_key=key)
    except stripe.error.StripeError as exc:
        raise ConnectOwnershipError("Não foi possível verificar a conta Stripe vinculada") from exc
    verify_account_owner(account, country, kind, owner_id)
    return True


async def collision_audit(db):
    """Read-only overview for admins; never exposes full bank details or emails."""
    registered = {}
    entries = []
    for label, collection in (("parceiro", "partners"), ("influenciador", "influencers")):
        async for item in db[collection].find({}, {"_id": 0, "id": 1, "nome": 1, "pais": 1,
                                                   "stripe_account_id": 1, "stripe_account_id_pt": 1,
                                                   "stripe_account_id_br": 1}):
            for field in ACCOUNT_FIELDS:
                account_id = item.get(field)
                if account_id:
                    entries.append({"kind": label, "id": item["id"], "nome": item.get("nome"),
                                    "country_field": field, "stripe_account_id": account_id})
                    registered.setdefault(account_id, []).append((label, item["id"]))
    collisions = [{"account_id": aid, "owners": [{"kind": kind, "id": oid} for kind, oid in owners]}
                  for aid, owners in registered.items() if len(set(owners)) > 1]
    missing_br = [e["id"] for e in entries if e["country_field"] == "stripe_account_id_br"]
    return {"accounts_mapped": len(registered), "collisions": collisions,
            "linked_br_records": len(missing_br), "entries": entries,
            "note": "Mesmo email ou banco não prova identidade; verificar titularidade na Stripe."}
