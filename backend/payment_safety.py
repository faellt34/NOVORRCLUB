"""Confirmação Stripe: Checkout concluído não é necessariamente pagamento recebido.

Pix e outros meios assíncronos podem ter status='complete' no Checkout
enquanto payment_status='unpaid'. Só o status 'paid' libera fulfilment.
"""


def is_payment_confirmed(session):
    """Retorna True somente quando a Stripe informa payment_status=paid."""
    if session is None:
        return False
    if hasattr(session, "get"):
        return session.get("payment_status") == "paid"
    return getattr(session, "payment_status", None) == "paid"


def is_legacy_eur_payment(record):
    """Only an existing EUR coupon or authenticated EUR product may use old fulfilment."""
    if not record or record.get("currency") != "eur":
        return False
    if record.get("kind") == "coupon_pay":
        return True
    return (
        not record.get("kind")
        and bool(record.get("lookup_key"))
        and bool(record.get("user_id"))
    )


def legacy_eur_fulfilment_filter(session_id):
    """Atomically refuse BR sandbox payments before mutating any receipt or access."""
    return {
        "session_id": session_id,
        "currency": "eur",
        "payment_status": {"$ne": "paid"},
        "$or": [
            {"kind": "coupon_pay"},
            {"kind": {"$exists": False}, "lookup_key": {"$exists": True},
             "user_id": {"$exists": True, "$ne": None}},
        ],
    }
