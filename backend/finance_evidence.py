"""Classificação conservadora de transferências; sem efeitos financeiros."""


def transfer_evidence(intent, charge=None, transfer=None, expected_amount=None, expected_destination=None):
    """Nunca equiparar payment_intent.succeeded a transferência ou payout bancário."""
    if intent.get("status") != "succeeded":
        return {"state": "payment_not_succeeded", "bank_payout": "not_verified"}
    if expected_amount is not None and intent.get("amount") != expected_amount:
        return {"state": "amount_mismatch", "bank_payout": "not_verified"}
    if not expected_destination:
        return {"state": "destination_unlinked", "bank_payout": "not_verified"}
    if not charge or not charge.get("transfer"):
        return {"state": "no_transfer_evidence", "bank_payout": "not_verified"}
    if not transfer or transfer.get("id") != charge.get("transfer"):
        return {"state": "transfer_not_verifiable", "bank_payout": "not_verified"}
    if transfer.get("destination") != expected_destination:
        return {"state": "destination_mismatch", "bank_payout": "not_verified"}
    if transfer.get("reversed") or transfer.get("amount_reversed", 0):
        return {"state": "reversed_or_partially_reversed", "bank_payout": "not_verified"}
    if not transfer.get("amount") or transfer.get("amount") <= 0:
        return {"state": "invalid_transfer_amount", "bank_payout": "not_verified"}
    return {"state": "transferred_to_connected_stripe_account", "bank_payout": "not_verified",
            "transfer_id": transfer.get("id"), "transfer_amount_minor": transfer.get("amount"),
            "transfer_currency": transfer.get("currency")}
