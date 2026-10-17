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
