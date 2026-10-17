"""Safety tests: never equate a shared email or bank account with a verified payout owner."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connect_identity import verify_account_owner, ConnectOwnershipError


def test_shared_email_not_proof_of_owner():
    account = {"country": "BR", "email": "faellt@gmail.com", "metadata": {},
               "payouts_enabled": True, "capabilities": {"transfers": "active"}}
    with pytest.raises(ConnectOwnershipError):
        verify_account_owner(account, "BR", "parceiros", "p123")


def test_matching_metadata_and_capabilities():
    account = {"country": "BR", "metadata": {"rrclub_owner_type": "parceiros", "rrclub_owner_id": "p123"},
               "payouts_enabled": True, "capabilities": {"transfers": "active"}}
    verify_account_owner(account, "BR", "parceiros", "p123")


def test_wrong_country_blocks():
    account = {"country": "PT", "metadata": {"partner_id": "p123"},
               "payouts_enabled": True, "capabilities": {"transfers": "active"}}
    with pytest.raises(ConnectOwnershipError):
        verify_account_owner(account, "BR", "parceiros", "p123")


def test_no_payouts_blocks():
    account = {"country": "BR", "metadata": {"partner_id": "p123"},
               "payouts_enabled": False, "capabilities": {"transfers": "inactive"}}
    with pytest.raises(ConnectOwnershipError):
        verify_account_owner(account, "BR", "parceiros", "p123")
