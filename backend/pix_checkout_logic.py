"""Regras puras para checkout Pix BR em sandbox; nenhuma transferência é executada."""
from urllib.parse import quote, urlsplit
from stripe_platform import PaymentConfigurationError


def require_sandbox_pix(config: dict) -> None:
    if config.get("country") != "BR" or config.get("currency") != "brl":
        raise PaymentConfigurationError("Checkout Pix de teste aceita somente campanhas do Brasil")
    if config.get("api_key", "").startswith("sk_live_"):
        raise PaymentConfigurationError("O checkout de teste nunca usa chave Stripe de produção")
    if not config.get("api_key", "").startswith("sk_test_"):
        raise PaymentConfigurationError("Configure a chave de teste Stripe Brasil")
    if not config.get("webhook_secret", "").startswith("whsec_"):
        raise PaymentConfigurationError("Configure o webhook brasileiro de teste antes de cobrar")


def frontend_return_urls(frontend_url: str, coupon: str) -> tuple[str, str]:
    url = (frontend_url or "").rstrip("/")
    p = urlsplit(url)
    local = p.hostname in ("localhost", "127.0.0.1")
    if (p.scheme != "https" and not (local and p.scheme == "http")) or not p.netloc or p.username or p.password or p.query or p.fragment:
        raise PaymentConfigurationError("FRONTEND_URL precisa ser um endereço seguro e válido")
    coupon_path = quote(coupon, safe="")
    return (f"{url}/c/{coupon_path}?session_id={{CHECKOUT_SESSION_ID}}",
            f"{url}/c/{coupon_path}?cancel=1")


def belongs_to_br_test_session(session: dict, record: dict) -> bool:
    """Check webhook object against server-side values before changing state."""
    meta = session.get("metadata") or {}
    return (
        session.get("id") == record.get("session_id")
        and session.get("livemode") is False
        and session.get("currency") == "brl"
        and session.get("amount_total") == record.get("amount_cents")
        and meta.get("kind") == "pix_br_test"
        and meta.get("country") == "BR"
        and meta.get("transaction_id") == record.get("id")
        and record.get("country") == "BR"
        and record.get("kind") == "pix_br_test"
        and record.get("currency") == "brl"
    )


def sandbox_payment_intent_data(transaction_id: str) -> dict:
    """Trace charge to future reconciliation; never create a transfer in sandbox."""
    if not isinstance(transaction_id, str) or not transaction_id.startswith("pixsandbox-") or len(transaction_id) > 120:
        raise PaymentConfigurationError("Identificador de transação Pix inválido")
    return {
        "transfer_group": f"rrclub_br_test_{transaction_id}",
        "metadata": {"kind": "pix_br_test", "country": "BR", "transaction_id": transaction_id},
    }
