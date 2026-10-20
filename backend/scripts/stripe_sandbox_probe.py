"""Read-only config and test-mode Checkout probes for RRClub PT and BR.

ONLY uses sk_test_ keys provided through GitHub Actions secrets.
Creates ephemeral TEST Checkout Sessions and expires them; never pays, captures,
calls Connect transfers, writes databases, publishes, or touches rrclub.online.
Not a proof of paid webhook delivery or settlement to connected recipients.
"""
import os
import sys
import uuid

import stripe

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from payments.stripe_normalize import stripe_payload


def safe_key(name):
    key = os.getenv(name, "").strip()
    if not key.startswith("sk_test_") or len(key) < 20:
        raise RuntimeError(f"{name} is missing or not a full sk_test_ secret")
    return key


def require_country(client, expected):
    account = stripe_payload(client.v1.accounts.retrieve_current())
    if account.get("country") != expected:
        raise RuntimeError(f"Wrong Stripe account region: expected {expected}")
    return account


def create_and_expire(client, params, label):
    """Perform only test-mode Checkout setup; no payment attempts."""
    key = "rrclub-safe-probe-" + uuid.uuid4().hex
    session = None
    try:
        session = stripe_payload(client.v1.checkout.sessions.create(
            params=params, options={"idempotency_key": key}
        ))
        if session.get("livemode") is not False or not str(session.get("id", "")).startswith("cs_test_"):
            raise RuntimeError(f"{label}: checkout is not confirmed to be test-mode")
        if not str(session.get("url", "")).startswith("https://checkout.stripe.com/"):
            raise RuntimeError(f"{label}: checkout URL was not returned")
        print(f"PASS {label}: test Checkout Session created; no payment made")
        return session
    finally:
        if session and str(session.get("id", "")).startswith("cs_test_"):
            try:
                client.v1.checkout.sessions.expire(session["id"])
                print(f"PASS {label}: test Checkout Session expired")
            except stripe.StripeError:
                print(f"WARNING {label}: test session could not be expired immediately")


def pt_probe():
    key = safe_key("RRCLUB_STRIPE_PT_TEST_KEY")
    client = stripe.StripeClient(key)
    account = require_country(client, "PT")
    print("PASS Portugal: test key and PT account verified")
    # A Checkout Session can show MB WAY only if it is enabled in this test account.
    session = create_and_expire(client, {
        "mode": "payment", "payment_method_types": ["mb_way"],
        "line_items": [{
            "price_data": {
                "currency": "eur", "unit_amount": 950,
                "product_data": {"name": "RRClub Sandbox P5 (nenhum pagamento)"},
            }, "quantity": 1,
        }],
        "metadata": {"kind": "rrclub_mbway_sandbox", "source": "github_actions_clone"},
        "success_url": "https://example.com/rrclub-sandbox/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://example.com/rrclub-sandbox/cancel",
    }, "Portugal MB WAY")
    if set(session.get("payment_method_types") or []) != {"mb_way"}:
        raise RuntimeError("Portugal: test Checkout is not MB WAY only")
    print("PASS Portugal: MB WAY only, 5% P5 simulated (10 EUR -> 9.50 EUR)")


def br_probe():
    key = safe_key("RRCLUB_STRIPE_BR_TEST_KEY")
    pmc_id = os.getenv("RRCLUB_STRIPE_BR_TEST_PMC", "").strip()
    if not pmc_id.startswith("pmc_"):
        raise RuntimeError("RRCLUB_STRIPE_BR_TEST_PMC must be a test-mode Pix-only payment method configuration")
    client = stripe.StripeClient(key)
    account = require_country(client, "BR")
    print("PASS Brazil: test key and BR account verified")
    config = stripe_payload(client.v1.payment_method_configurations.retrieve(pmc_id))
    enabled = sorted(
        name for name, value in config.items()
        if isinstance(value, dict)
        and value.get("available") is True
        and (value.get("display_preference") or {}).get("value") == "on"
    )
    if config.get("livemode") is not False or config.get("active") is not True or enabled != ["pix"]:
        raise RuntimeError("Brazil: payment method configuration is not active Pix-only TEST mode")
    print("PASS Brazil: Pix-only payment method configuration verified")
    session = create_and_expire(client, {
        "mode": "payment", "payment_method_configuration": pmc_id,
        "line_items": [{
            "price_data": {
                "currency": "brl", "unit_amount": 950,
                "product_data": {"name": "RRClub Pix Sandbox P5 (nenhum pagamento)"},
            }, "quantity": 1,
        }],
        "metadata": {"kind": "rrclub_pix_sandbox", "source": "github_actions_clone"},
        "success_url": "https://example.com/rrclub-sandbox/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://example.com/rrclub-sandbox/cancel",
    }, "Brazil Pix")
    if list(session.get("payment_method_types") or []) != ["pix"]:
        raise RuntimeError("Brazil: Checkout is not Pix-only")
    print("PASS Brazil: Pix-only and 5% P5 simulated (10 BRL -> 9.50 BRL)")


if __name__ == "__main__":
    # Fail before any provider call when either key is absent or potentially live.
    try:
        safe_key("RRCLUB_STRIPE_PT_TEST_KEY")
        safe_key("RRCLUB_STRIPE_BR_TEST_KEY")
        if not os.getenv("RRCLUB_STRIPE_BR_TEST_PMC", "").startswith("pmc_"):
            raise RuntimeError("Missing test-only Pix payment method configuration")
        pt_probe()
        br_probe()
        print("NOTE: paid webhooks, captures, Connect transfers and bank deposits are NOT tested here.")
    except (stripe.StripeError, RuntimeError, ValueError) as exc:
        # Avoid logging secrets or raw provider objects.
        message = str(exc)
        for env_name in ("RRCLUB_STRIPE_PT_TEST_KEY", "RRCLUB_STRIPE_BR_TEST_KEY"):
            secret = os.getenv(env_name, "")
            if secret:
                message = message.replace(secret, "[REDACTED]")
        print(f"FAIL sandbox verification: {message[:500]}", file=sys.stderr)
        sys.exit(1)
