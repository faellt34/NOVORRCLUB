"""Mandatory isolation checks before a RRClub clone server can touch its DB.

This module belongs only on BRANCH-copia-editar-a-vontade.
Forbids production domain, DB name or live Stripe keys in this clone.
"""
import os
from urllib.parse import urlsplit


def require_isolated_clone():
    if os.environ.get("RRCLUB_CLONE_ISOLATED", "").lower() != "true":
        raise RuntimeError("Clone locked: set RRCLUB_CLONE_ISOLATED=true only on a separate deployment.")
    db_name = os.environ.get("DB_NAME", "")
    if not db_name.startswith("rrclub_clone_") or len(db_name) < len("rrclub_clone_")+3:
        raise RuntimeError("Clone locked: use a separate DB_NAME beginning rrclub_clone_.")
    for key in ("STRIPE_SECRET_KEY", "PIX_STRIPE_SECRET_KEY", "MBWAY_PT_SANDBOX_SECRET_KEY"):
        value = os.environ.get(key, "")
        if value and (not value.startswith("sk_test_") or len(value) < 20):
            raise RuntimeError("Clone locked: all supplied Stripe secrets must be sk_test_.")
    front = os.environ.get("FRONTEND_URL", "")
    if not front:
        raise RuntimeError("Clone locked: FRONTEND_URL must identify a separate HTTPS preview.")
    url = urlsplit(front)
    if url.scheme != "https" or not url.hostname or url.hostname.lower() in (
        "rrclub.online", "www.rrclub.online",
    ):
        raise RuntimeError("Clone locked: production domain not allowed.")
    allowed = [x.strip() for x in os.environ.get("PAYMENT_ALLOWED_ORIGINS", "").split(",") if x.strip()]
    for entry in allowed:
        parsed = urlsplit(entry)
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() in (
            "rrclub.online", "www.rrclub.online",
        ):
            raise RuntimeError("Clone locked: payment allowlist contains a production or non-HTTPS origin.")
    if os.environ.get("PT_SPLIT_V2_ENABLED", "").lower() == "true" and not os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
        raise RuntimeError("Clone locked: PT split requires sk_test_ credentials.")
    return True
