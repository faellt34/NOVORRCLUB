"""Country-scoped Stripe configuration. Never use the other country's key as fallback."""
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from payment_region import resolve_payment_region, PaymentRegionError


class PaymentConfigurationError(ValueError):
    pass


def stripe_config(campaign, partner):
    try:
        region = resolve_payment_region(campaign, partner)
    except PaymentRegionError as exc:
        raise PaymentConfigurationError(str(exc)) from exc
    country = region["country"]
    key = os.environ.get(region["stripe_key_env"], "")
    # No global STRIPE_SECRET_KEY fallback: otherwise BR may be billed by PT.
    if not key.startswith(("sk_live_", "sk_test_")):
        raise PaymentConfigurationError("A chave Stripe da operação " + country + " não está configurada")
    if country == "BR" and os.environ.get("PIX_ENABLED", "false").lower() != "true":
        raise PaymentConfigurationError("Pix está desativado até a configuração brasileira ser validada")
    region["api_key"] = key
    region["webhook_secret"] = os.environ.get("STRIPE_WEBHOOK_SECRET_" + country, "")
    return region


def amount_cents(value):
    try:
        v = Decimal(str(value))
    except (ValueError, InvalidOperation):
        raise PaymentConfigurationError("Valor monetário inválido")
    if not v.is_finite() or v < 0:
        raise PaymentConfigurationError("Valor monetário deve ser finito e não negativo")
    return int((v * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent_cents(gross_cents, rate):
    try:
        pct = Decimal(str(rate))
    except (ValueError, InvalidOperation):
        raise PaymentConfigurationError("Percentagem inválida")
    if not pct.is_finite() or not (Decimal("0") <= pct <= Decimal("100")):
        raise PaymentConfigurationError("Percentagem deve estar entre 0 e 100")
    return int((Decimal(gross_cents) * pct / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def transfer_account(person, country):
    """Legacy unsuffixed Connect IDs are PT only; BR always has its own field."""
    if country == "BR":
        return person.get("stripe_account_id_br") if person.get("stripe_country_br", "BR") == "BR" else None
    if country == "PT":
        return person.get("stripe_account_id_pt") or (
            person.get("stripe_account_id") if person.get("stripe_country", "PT") == "PT" else None)
    return None


def split_snapshot(gross_cents, campaign):
    discount = percent_cents(gross_cents, campaign.get("desconto", 0))
    paid = gross_cents - discount
    if paid <= 0:
        raise PaymentConfigurationError("O desconto não pode consumir toda a compra")
    if "comissao_rrclub" not in campaign or campaign["comissao_rrclub"] in ("", None):
        raise PaymentConfigurationError("Defina a comissão RRClub (%) na campanha antes de cobrar e repartir")
    influencer = percent_cents(gross_cents, campaign.get("comissao", 0))
    rrclub = percent_cents(gross_cents, campaign["comissao_rrclub"])
    partner = paid - rrclub - influencer
    if partner < 0:
        raise PaymentConfigurationError("Comissões ultrapassam o valor após desconto")
    return {"gross_cents": gross_cents, "discount_cents": discount, "paid_cents": paid,
            "rrclub_cents": rrclub, "influencer_cents": influencer, "partner_cents": partner}
