"""Separação determinística de operações RRClub Brasil e Portugal.

Não infere país pela cidade, moeda ou origem do navegador. A campanha e/ou
o parceiro precisam declarar o país; dados conflitantes bloqueiam cobrança.
"""


class PaymentRegionError(ValueError):
    pass


REGIONS = {
    "BR": {"country": "BR", "currency": "brl", "payment_methods": ("pix",), "stripe_key_env": "STRIPE_SECRET_KEY_BR"},
    "PT": {"country": "PT", "currency": "eur", "payment_methods": ("card", "mb_way"), "stripe_key_env": "STRIPE_SECRET_KEY_PT"},
}


def normalize_country(value):
    if not isinstance(value, str) or not value.strip():
        return None
    key = value.strip().casefold()
    return {"br": "BR", "brasil": "BR", "brazil": "BR",
            "pt": "PT", "portugal": "PT"}.get(key)


def resolve_payment_region(campaign: dict, partner: dict) -> dict:
    country_values = []
    for label, obj in (("campanha", campaign), ("parceiro", partner)):
        raw = obj.get("pais") or obj.get("country")
        if raw:
            country = normalize_country(raw)
            if not country:
                raise PaymentRegionError(f"País inválido no cadastro do {label}; operação bloqueada")
            country_values.append(country)
    if not country_values:
        raise PaymentRegionError("Defina o país do parceiro ou da campanha antes de cobrar")
    if len(set(country_values)) != 1:
        raise PaymentRegionError("País da campanha e do parceiro não correspondem; cobrança bloqueada")
    return dict(REGIONS[country_values[0]])
