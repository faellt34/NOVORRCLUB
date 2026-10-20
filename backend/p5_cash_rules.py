"""P5: arithmetic and state transitions for cash payments; no Stripe processing."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class CashRuleError(ValueError):
    pass


def dec(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise CashRuleError("Número inválido")
    if not n.is_finite():
        raise CashRuleError("Número inválido")
    return n


def money(value):
    return dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percentage(value):
    n = dec(value)
    if n < 0 or n > 100:
        raise CashRuleError("Percentagem inválida")
    return n


def quote_cash(gross, discount_pct, commission_pct, currency="eur"):
    value = money(gross)
    discount_pct = percentage(discount_pct)
    commission_pct = percentage(commission_pct)
    currency = str(currency).lower()
    if currency not in ("eur", "brl"):
        raise CashRuleError("Moeda não suportada")
    if value <= 0 or value > 10000:
        raise CashRuleError("Valor inválido")
    discount = money(value * discount_pct / 100)
    payable = value - discount
    commission = money(value * commission_pct / 100)
    if commission > payable:
        raise CashRuleError("Comissão superior ao valor a pagar")
    return {
        "gross": str(value),
        "discount": str(discount),
        "payable": str(payable),
        "commission_owed": str(commission),
        "currency": currency,
        "method": "cash",
        "payment_status": "pending_cash",
        "commission_status": "owed_by_partner",
        "stripe_status": "not_applicable",
    }


def confirm_cash(status, received, authorized, matched_partner):
    if status != "pending_cash":
        raise CashRuleError("Operação não está pendente")
    if not (authorized and matched_partner):
        raise CashRuleError("Parceiro não autorizado")
    if received is not True:
        raise CashRuleError("Dinheiro ainda não recebido")
    return "cash_confirmed_by_partner"
