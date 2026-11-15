"""Read-only Stripe Connect snapshot validation used by admin sync.

Never assigns account owners, changes Stripe state, or enables checkout.
"""
from collections.abc import Mapping


class ConnectSyncError(ValueError):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def resolve_target(partner: Mapping, env: Mapping):
    """Choose only the account already recorded for this partner and country."""
    currency = str(partner.get("currency") or "eur").lower()
    if currency not in ("eur", "brl"):
        raise ConnectSyncError("Moeda do parceiro não suportada")
    field = "pix_stripe_account_id" if currency == "brl" else "stripe_account_id"
    account_id = partner.get(field)
    if not isinstance(account_id, str) or not account_id.startswith("acct_") or len(account_id) <= 8:
        raise ConnectSyncError("A conta Stripe Connect deste parceiro ainda não está associada")
    if currency == "brl" and env.get("PIX_STRIPE_PLATFORM_COUNTRY") != "BR":
        raise ConnectSyncError("A plataforma Stripe Brasil não está configurada", 503)
    key_name = "PIX_STRIPE_SECRET_KEY" if currency == "brl" else "STRIPE_SECRET_KEY"
    key = env.get(key_name) or ""
    if not isinstance(key, str) or not key.startswith(("sk_live_", "sk_test_", "rk_live_", "rk_test_")):
        raise ConnectSyncError("A chave de consulta Stripe deste país não está configurada", 503)
    return field, account_id, key, ("BR" if currency == "brl" else "PT"), currency


def verified_snapshot(partner: Mapping, account: Mapping, expected_account_id: str, country: str, timestamp: str):
    """Fail closed on ownership mismatch; store only booleans and verification date."""
    if account.get("id") != expected_account_id:
        raise ConnectSyncError("A conta devolvida pela Stripe não corresponde à associação guardada")
    if account.get("country") != country:
        raise ConnectSyncError("A conta Stripe pertence a um país diferente do parceiro")
    if (account.get("metadata") or {}).get("partner_id") != partner.get("id"):
        raise ConnectSyncError("Identificação do parceiro não confirmada nos metadados Stripe")
    charges = account.get("charges_enabled")
    payouts = account.get("payouts_enabled")
    if not isinstance(charges, bool) or not isinstance(payouts, bool):
        raise ConnectSyncError("A Stripe não devolveu estados verificáveis de cobrança/recebimento", 502)
    transfers = (account.get("capabilities") or {}).get("transfers") == "active"
    requirements = account.get("requirements") or {}
    due = bool(requirements.get("currently_due") or requirements.get("past_due") or requirements.get("disabled_reason"))
    ready = charges and payouts and transfers and not due
    return {
        "charges_enabled_cached": charges,
        "payouts_enabled_cached": payouts,
        "transfers_enabled_cached": transfers,
        "connect_ready_cached": bool(ready),
        "ultima_consulta_confirmada": timestamp,
    }
