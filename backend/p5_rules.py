"""P5's server-owned monetary calculation for Portugal (EUR) and Brasil (BRL).

All arithmetic is performed using Decimal and integer minor units.
The follower never supplies a bill total or percent to the checkout endpoint.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class P5QuoteError(ValueError):
    pass


def finite(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite():
            raise P5QuoteError("Valor financeiro inválido")
        return n
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise P5QuoteError("Valor financeiro inválido") from exc


def quote_minor(gross, discount_pct, commission_pct, currency):
    c = str(currency).lower()
    if c not in ("eur", "brl"):
        raise P5QuoteError("Moeda inválida")
    amount, discount, commission = finite(gross), finite(discount_pct), finite(commission_pct)
    if not Decimal("0.01") <= amount <= Decimal("10000"):
        raise P5QuoteError("Valor de compra inválido")
    if not Decimal("0") <= discount < Decimal("100"):
        raise P5QuoteError("Desconto inválido")
    if not Decimal("0") <= commission < Decimal("100"):
        raise P5QuoteError("Comissão inválida")
    if c in ("eur", "brl") and (discount != 5 or commission != 5):
        raise P5QuoteError("P5 Portugal/Brasil requer 5% de desconto e 5% de comissão")
    gross_cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    discount_cents = int(
        (Decimal(gross_cents) * discount / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    net = gross_cents - discount_cents
    if net < 50:
        raise P5QuoteError("Total após desconto inferior ao mínimo")
    return {
        "currency": c,
        "gross_minor": gross_cents,
        "discount_minor": discount_cents,
        "net_minor": net,
        "commission_percent_snapshot": str(commission),
    }
