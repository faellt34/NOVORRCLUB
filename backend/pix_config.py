"""Fail-closed validation for RRClub Brazil Pix runtime settings.

No credentials are persisted, logged, generated, or included in responses.
This module never contacts Stripe and cannot prove a payment has settled.
"""
import os
from urllib.parse import urlsplit

# Public ID confirmed active and Pix-only on RRCLUBRASIL (livemode).
# Not a secret. Never use this fallback for testmode or another country.
BRAZIL_LIVE_PIX_CONFIGURATION_ID = "pmc_1URqMREKAxcuX59L1ExKvQ7V"


def pix_payment_method_configuration(env=None):
    env = os.environ if env is None else env
    explicit = env.get("PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION", "")
    if explicit:
        return explicit
    key = env.get("PIX_STRIPE_SECRET_KEY", "")
    if (_is_key(key) and key.startswith(("sk_live_", "rk_live_"))
            and env.get("PIX_STRIPE_PLATFORM_COUNTRY") == "BR"
            and key != env.get("STRIPE_SECRET_KEY", "")):
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
    pix_key = env.get("PIX_STRIPE_SECRET_KEY", "")
    pt_key = env.get("STRIPE_SECRET_KEY", "")
    method = pix_payment_method_configuration(env)
    webhook_secret = env.get("PIX_STRIPE_WEBHOOK_SECRET", "")
    origins = env.get("PAYMENT_ALLOWED_ORIGINS", "") or env.get("FRONTEND_URL", "")
    origin_list = [origin.strip() for origin in origins.split(",") if origin.strip()]
    checks = {
        "api_key": _is_key(pix_key),
        "platform_country_br": env.get("PIX_STRIPE_PLATFORM_COUNTRY") == "BR",
        "separate_brazil_key": not (_is_key(pix_key) and pix_key == pt_key),
        "webhook": isinstance(webhook_secret, str) and webhook_secret.startswith("whsec_")
                   and len(webhook_secret) > len("whsec_"),
        "payment_method_configuration": isinstance(method, str)
                   and method.startswith("pmc_") and len(method) > 4,
        "allowed_origins": bool(origin_list) and all(map(_is_https_origin, origin_list)),
    }
    configured = all(checks.values())
    enabled = env.get("PIX_ENABLED", "false").lower() == "true"
    return {"configured": configured, "enabled": enabled,
            "accepting_new_payments": configured and enabled}, checks
