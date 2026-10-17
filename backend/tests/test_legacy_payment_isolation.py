"""Protect EUR legacy flow from Brazilian sandbox sessions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from payment_safety import is_legacy_eur_payment, legacy_eur_fulfilment_filter


def test_legacy_eur_recognizes_only_known_operations():
    assert is_legacy_eur_payment({"currency": "eur", "kind": "coupon_pay"})
    assert is_legacy_eur_payment({"currency": "eur", "lookup_key": "ebook_1", "user_id": "u1"})
    assert not is_legacy_eur_payment({"currency": "brl", "kind": "pix_br_test"})
    assert not is_legacy_eur_payment({"currency": "eur", "kind": "pix_br_test"})
    assert not is_legacy_eur_payment({"currency": "eur", "lookup_key": "ebook_1"})
    assert not is_legacy_eur_payment({"currency": "eur", "kind": "unknown"})


def test_legacy_filter_never_matches_br_pix():
    filter_ = legacy_eur_fulfilment_filter("cs_test_01")
    assert filter_["currency"] == "eur"
    assert filter_["session_id"] == "cs_test_01"
    assert filter_["payment_status"] == {"$ne": "paid"}
    assert {"kind": "coupon_pay"} in filter_["$or"]
    assert all(condition.get("kind") != "pix_br_test" for condition in filter_["$or"])
