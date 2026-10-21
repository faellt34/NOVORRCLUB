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
