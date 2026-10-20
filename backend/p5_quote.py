"""P5: server-side quotations in Portugal and Brazil. No charges are created."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

class QuoteError(ValueError):
    pass

COUNTRIES = {"PT": ("eur", ("mb_way", "card", "apple_pay", "cash")),
             "BR": ("brl", ("pix", "card", "apple_pay", "cash"))}

def number(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise QuoteError("Número inválido")
    if not n.is_finite():
        raise QuoteError("Número inválido")
    return n

def quote(gross, discount_pct, country):
    """Use only a discount percentage loaded from the approved campaign on the server."""
    country = str(country).upper()
    if country not in COUNTRIES:
        raise QuoteError("País inválido")
    gross = number(gross)
    pct = number(discount_pct)
    if gross <= 0 or gross > 10000 or pct < 0 or pct >= 100:
        raise QuoteError("Valor ou desconto inválido")
    amount = gross.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    reduction = (amount * pct / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    due = amount - reduction
    if due <= 0:
        raise QuoteError("Total inválido")
    currency, methods = COUNTRIES[country]
    return {"country": country, "currency": currency, "gross": str(amount),
            "discount_pct": str(pct), "discount": str(reduction),
            "payable": str(due), "candidate_methods": methods,
            "payment_status": "not_paid"}
