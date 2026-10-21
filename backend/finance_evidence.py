"""Classificação conservadora de provas financeiras da Stripe (somente leitura).

Não considerar payment_intent.succeeded como transferência nem transferência
para Connect como payout bancário.
"""

def transfer_evidence(intent, charge=None, transfer=None, expected_amount=None,
                      expected_destination=None):
    if intent.get("status") != "succeeded":
        return {"state": "payment_not_succeeded", "bank_payout": "not_verified"}
    if str(intent.get("currency") or "").lower() != "eur":
        return {"state": "payment_currency_mismatch", "bank_payout": "not_verified"}
    if expected_amount is not None and intent.get("amount") != expected_amount:
        return {"state": "amount_mismatch", "bank_payout": "not_verified"}
    if not expected_destination:
        return {"state": "destination_unlinked", "bank_payout": "not_verified"}
    if charge and (charge.get("refunded") or (charge.get("amount_refunded") or 0) > 0):
        return {"state": "charge_refunded_or_partially_refunded", "bank_payout": "not_verified"}
    if charge and charge.get("disputed"):
        return {"state": "charge_disputed", "bank_payout": "not_verified"}
    if not charge or not charge.get("transfer"):
        return {"state": "no_transfer_evidence", "bank_payout": "not_verified"}
    transfer_id = charge.get("transfer")
    if hasattr(transfer_id, "get"):
        transfer_id = transfer_id.get("id")
    if not transfer or transfer.get("id") != transfer_id:
        return {"state": "transfer_not_verifiable", "bank_payout": "not_verified"}
    if transfer.get("destination") != expected_destination:
        return {"state": "destination_mismatch", "bank_payout": "not_verified"}
    if transfer.get("reversed") or transfer.get("amount_reversed", 0):
        return {"state": "reversed_or_partially_reversed", "bank_payout": "not_verified"}
    if transfer.get("currency") != "eur" or (transfer.get("amount") or 0) <= 0:
        return {"state": "invalid_transfer_amount_or_currency", "bank_payout": "not_verified"}
    return {
        "state": "transferred_to_connected_stripe_account",
        "bank_payout": "not_verified",
        "transfer_id": transfer.get("id"),
        "transfer_amount_minor": transfer.get("amount"),
        "transfer_currency": transfer.get("currency"),
    }


def connect_account_evidence(account, expected_partner_id):
    """Prova de associação e aptidão Connect, por IDs. Nunca por nome comercial.

    Sem associação explícita por metadata.partner_id, não se pode aprovar
    automaticamente uma transferência, mesmo que o nome pareça correto.
    """
    if not account:
        return {
            "account_link_verified": "unverified",
            "charges_enabled": False,
            "payouts_enabled": False,
            "transfers_active": False,
            "requirements_pending": False,
            "disabled_reason": None,
            "ready_for_partner_transfer": False,
        }
    partner_id = (account.get("metadata") or {}).get("partner_id")
    linked_status = (
        "verified" if partner_id and partner_id == expected_partner_id
        else "mismatch" if partner_id
        else "unverified"
    )
    charges = bool(account.get("charges_enabled"))
    payouts = bool(account.get("payouts_enabled"))
    transfers = (account.get("capabilities") or {}).get("transfers") == "active"
    due = bool((account.get("requirements") or {}).get("currently_due"))
    return {
        "account_link_verified": linked_status,
        "charges_enabled": charges,
        "payouts_enabled": payouts,
        "transfers_active": transfers,
        "requirements_pending": due,
        "disabled_reason": (account.get("requirements") or {}).get("disabled_reason"),
        "ready_for_partner_transfer": bool(linked_status == "verified" and charges and payouts and transfers and not due),
    }
