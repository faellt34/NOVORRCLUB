"""Fail-closed validation for RRClub Brazil Pix runtime settings.

No credentials are persisted, logged, generated, or included in responses.
This module never contacts Stripe and cannot prove a payment has settled.
"""
import os
from urllib.parse import urlsplit

# Public ID confirmed active and Pix-only on RRCLUBRASIL (livemode).
# Not a secret. Never use this fallback for testmode or another country.
BRAZIL_LIVE_PIX_CONFIGURATION_ID = "pmc_1URqMREKAxcuX59L1ExKvQ7V"


def _clean(value):
    return value.strip().strip('"\'').strip() if isinstance(value, str) else ""


def _key_hint(value):
    raw = value if isinstance(value, str) else ""
    v = _clean(raw)
    if not v:
        return "vazio"
    if v.startswith("pk_"):
        return "chave publicável (pk_) — é necessária a chave secreta sk_/rk_"
    if not v.startswith(("sk_live_", "rk_live_", "sk_test_", "rk_test_")):
        return "prefixo inválido (esperado sk_live_/rk_live_/sk_test_/rk_test_)"
    if len(v) <= 12:
        return "demasiado curta"
    return "ok"


def pix_payment_method_configuration(env=None):
    env = os.environ if env is None else env
    explicit = _clean(env.get("PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION", ""))
    if explicit:
        return explicit
    key = _clean(env.get("PIX_STRIPE_SECRET_KEY", ""))
    if (_is_key(key) and key.startswith(("sk_live_", "rk_live_"))
            and _clean(env.get("PIX_STRIPE_PLATFORM_COUNTRY", "")) == "BR"
            and key != _clean(env.get("STRIPE_SECRET_KEY", ""))):
        return BRAZIL_LIVE_PIX_CONFIGURATION_ID
    return ""



def _is_key(value):
    return isinstance(value, str) and value.startswith((
        "sk_live_", "rk_live_", "sk_test_", "rk_test_"
    )) and len(value) > 12


def _is_https_origin(value):
    value = value.strip()
    if not value:
        return False
    parsed = urlsplit(value)
    return (parsed.scheme == "https" and bool(parsed.netloc)
            and not parsed.username and not parsed.password
            and parsed.path in ("", "/") and not parsed.query
            and not parsed.fragment)


def configuration_status(env=None):
    """Return (public state, per-field checks) without exposing secret values.

    Validating prefixes is only a local sanity check, not Stripe verification.
    """
    env = os.environ if env is None else env
    pix_key = _clean(env.get("PIX_STRIPE_SECRET_KEY", ""))
    pt_key = _clean(env.get("STRIPE_SECRET_KEY", ""))
    method = pix_payment_method_configuration(env)
    webhook_secret = _clean(env.get("PIX_STRIPE_WEBHOOK_SECRET", ""))
    origins = env.get("PAYMENT_ALLOWED_ORIGINS", "") or env.get("FRONTEND_URL", "")
    origin_list = [origin.strip() for origin in origins.split(",") if origin.strip()]
    checks = {
        "api_key": _is_key(pix_key),
        "api_key_hint": _key_hint(env.get("PIX_STRIPE_SECRET_KEY", "")),
        "platform_country_br": _clean(env.get("PIX_STRIPE_PLATFORM_COUNTRY", "")) == "BR",
        "separate_brazil_key": not (_is_key(pix_key) and pix_key == pt_key),
        "webhook": isinstance(webhook_secret, str) and webhook_secret.startswith("whsec_")
                   and len(webhook_secret) > len("whsec_"),
        "payment_method_configuration": isinstance(method, str)
                   and method.startswith("pmc_") and len(method) > 4,
        "allowed_origins": bool(origin_list) and all(map(_is_https_origin, origin_list)),
    }
    configured = all(v for k, v in checks.items() if k != "api_key_hint")
    enabled = env.get("PIX_ENABLED", "false").lower() == "true"
    return {"configured": configured, "enabled": enabled,
            "accepting_new_payments": configured and enabled}, checks
