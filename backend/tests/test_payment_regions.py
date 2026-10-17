"""Testes unitários sem Stripe nem banco de dados externo."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from payment_region import PaymentRegionError, resolve_payment_region
from payment_safety import is_payment_confirmed


@pytest.mark.parametrize("session,expected", [
    ({"status": "complete", "payment_status": "unpaid"}, False),
    ({"status": "complete", "payment_status": "paid"}, True),
    ({"status": "open", "payment_status": "unpaid"}, False),
    ({"status": "complete"}, False),
    (None, False),
    ({"status": "complete", "payment_status": "processing"}, False),
])
def test_payment_confirmed_requires_stripe_paid(session, expected):
    assert is_payment_confirmed(session) is expected


def test_portugal_card_mb_way_euro():
    region = resolve_payment_region({"pais": "Portugal"}, {"pais": "PT"})
    assert region["currency"] == "eur"
    assert region["payment_methods"] == ("card", "mb_way")
    assert region["stripe_key_env"] == "STRIPE_SECRET_KEY_PT"


def test_brasil_pix_brl():
    region = resolve_payment_region({"pais": "Brasil"}, {"pais": "BR"})
    assert region["currency"] == "brl"
    assert region["payment_methods"] == ("pix",)
    assert region["stripe_key_env"] == "STRIPE_SECRET_KEY_BR"


@pytest.mark.parametrize("campaign,partner", [
    ({}, {}),
    ({"pais": "Brasil"}, {"pais": "Portugal"}),
    ({"pais": "Marte"}, {}),
    ({}, {"pais": "Desconhecido"}),
])
def test_ambiguous_or_conflicting_country_blocks_payment(campaign, partner):
    with pytest.raises(PaymentRegionError):
        resolve_payment_region(campaign, partner)
