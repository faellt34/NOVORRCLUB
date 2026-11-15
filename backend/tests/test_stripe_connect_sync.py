"""Offline security and status tests: no Stripe network, database or charges."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stripe_connect_sync import ConnectSyncError, resolve_target, verified_snapshot


class ConnectSyncTests(unittest.TestCase):
    def setUp(self):
        self.partner = {"id": "p-identified", "currency": "brl", "pix_stripe_account_id": "acct_1234567890"}
        self.env = {"PIX_STRIPE_PLATFORM_COUNTRY": "BR", "PIX_STRIPE_SECRET_KEY": "sk_test_FAKENETWORKDISABLED"}
        self.account = {
            "id": "acct_1234567890", "country": "BR", "metadata": {"partner_id": "p-identified"},
            "charges_enabled": True, "payouts_enabled": True,
            "capabilities": {"transfers": "active"}, "requirements": {"currently_due": [], "past_due": [], "disabled_reason": None},
        }

    def test_brasil_uses_only_brazil_credential_and_existing_id(self):
        field, account_id, key, country, currency = resolve_target(self.partner, self.env)
        self.assertEqual((field, account_id, country, currency),
                         ("pix_stripe_account_id", "acct_1234567890", "BR", "brl"))
        self.assertTrue(key.startswith("sk_test_"))

    def test_portugal_never_uses_pix_credentials(self):
        p = {"id": "p-eur", "currency": "eur", "stripe_account_id": "acct_9876543210"}
        env = {"STRIPE_SECRET_KEY": "sk_test_FAKENETWORKDISABLED"}
        self.assertEqual(resolve_target(p, env)[0:2], ("stripe_account_id", "acct_9876543210"))
        self.assertEqual(resolve_target(p, env)[3:], ("PT", "eur"))

    def test_unknown_account_never_assigned(self):
        self.partner.pop("pix_stripe_account_id")
        with self.assertRaises(ConnectSyncError):
            resolve_target(self.partner, self.env)

    def test_missing_key_does_not_allow_sync(self):
        with self.assertRaises(ConnectSyncError) as err:
            resolve_target(self.partner, {"PIX_STRIPE_PLATFORM_COUNTRY": "BR"})
        self.assertEqual(err.exception.status_code, 503)

    def test_metadata_mismatch_fails_closed(self):
        self.account["metadata"] = {}
        with self.assertRaises(ConnectSyncError):
            verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")

    def test_cross_border_account_fails_closed(self):
        self.account["country"] = "PT"
        with self.assertRaises(ConnectSyncError):
            verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")

    def test_wrong_account_id_fails_closed(self):
        with self.assertRaises(ConnectSyncError):
            verified_snapshot(self.partner, self.account, "acct_other_id", "BR", "timestamp")

    def test_unknown_provider_flags_do_not_clear_cache(self):
        self.account.pop("charges_enabled")
        with self.assertRaises(ConnectSyncError):
            verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")

    def test_eligible_account_has_verified_cache(self):
        snapshot = verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")
        self.assertTrue(snapshot["connect_ready_cached"])
        self.assertEqual(snapshot["ultima_consulta_confirmada"], "timestamp")
        self.assertTrue(snapshot["charges_enabled_cached"])

    def test_inactive_account_returns_false_not_false_positive(self):
        self.account["charges_enabled"] = False
        self.account["requirements"]["disabled_reason"] = "requirements.past_due"
        snapshot = verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")
        self.assertFalse(snapshot["connect_ready_cached"])
        self.assertFalse(snapshot["charges_enabled_cached"])

    def test_pending_transfers_means_not_ready(self):
        self.account["capabilities"]["transfers"] = "inactive"
        snapshot = verified_snapshot(self.partner, self.account, "acct_1234567890", "BR", "timestamp")
        self.assertFalse(snapshot["connect_ready_cached"])


if __name__ == "__main__":
    unittest.main()
