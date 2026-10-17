"""Validacao de novos cadastros financeiros RRClub; preserva legados sem migração."""
import math
from payment_region import normalize_country


def validate_admin_payment_fields(kind, data, creating=False, existing=None):
    """Return sanitized copy; fail closed on new identities and BR commissions."""
    values = dict(data)
    if kind not in ("parceiros", "influencers", "campanhas"):
        return values
    raw = values.get("pais")
    if raw is not None:
        country = normalize_country(raw)
        if not country:
            if creating or str(raw).strip():
                raise ValueError("Escolha explicitamente o país BR ou PT")
            values.pop("pais")
        else:
            values["pais"] = country
    elif creating:
        raise ValueError("País BR ou PT obrigatório em novos cadastros")

    if kind != "campanhas":
        return values
    for field in ("desconto", "comissao", "comissao_rrclub"):
        if field not in values:
            continue
        val = values[field]
        if (val is None or str(val).strip() == "") and field == "comissao_rrclub":
            values.pop(field)
            continue
        try:
            numeric = float(str(val).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError(f"Percentual inválido em {field}")
        if not math.isfinite(numeric) or not (0 <= numeric <= 100):
            raise ValueError(f"{field} deve estar entre 0 e 100")
        values[field] = numeric
    candidate = {**(existing or {}), **values}
    if normalize_country(candidate.get("pais")) == "BR":
        if candidate.get("comissao_rrclub") in (None, ""):
            raise ValueError("Comissão própria da RRClub é obrigatória na campanha brasileira")
        discount = candidate.get("desconto")
        influencer = candidate.get("comissao")
        rrclub = candidate.get("comissao_rrclub")
        if all(isinstance(v, (int, float)) for v in (discount, influencer, rrclub)):
            if discount + influencer + rrclub > 100:
                raise ValueError("Desconto e comissões excedem 100% do valor bruto")
    return values


def legacy_eur_checkout_allowed(campaign, partner):
    """Only known PT or pre-existing unclassified records may use old EUR path."""
    for item in (campaign, partner):
        raw = item.get("pais") or item.get("country")
        if raw and normalize_country(raw) != "PT":
            return False
    return True
