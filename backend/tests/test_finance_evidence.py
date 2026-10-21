import unittest
from finance_evidence import transfer_evidence, connect_account_evidence


class FinanceEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.pi = {"status": "succeeded", "amount": 90, "currency": "eur"}
        self.charge = {"transfer": "tr_unit"}
        self.transfer = {"id": "tr_unit", "destination": "acct_partner", "amount": 85,
                         "amount_reversed": 0, "reversed": False, "currency": "eur"}

    def test_received_not_transferred(self):
        self.assertEqual(transfer_evidence(self.pi, None, None, 90, "acct_partner")["state"],
                         "no_transfer_evidence")

    def test_paid_does_not_mean_bank_payout(self):
        r = transfer_evidence(self.pi, self.charge, self.transfer, 90, "acct_partner")
        self.assertEqual(r["state"], "transferred_to_connected_stripe_account")
        self.assertEqual(r["bank_payout"], "not_verified")

    def test_wrong_amount(self):
        self.assertEqual(transfer_evidence(self.pi, self.charge, self.transfer, 91, "acct_partner")["state"], "amount_mismatch")

    def test_wrong_currency(self):
        self.assertEqual(transfer_evidence({**self.pi, "currency": "brl"}, self.charge, self.transfer, 90, "acct_partner")["state"],
                         "payment_currency_mismatch")

    def test_refunded_charge_cannot_be_confirmed_as_transferred(self):
        refunded = {**self.charge, "refunded": True, "amount_refunded": 90}
        self.assertEqual(
            transfer_evidence(self.pi, refunded, self.transfer, 90, "acct_partner")["state"],
            "charge_refunded_or_partially_refunded"
        )

    def test_disputed_charge_cannot_be_confirmed_as_transferred(self):
        disputed = {**self.charge, "disputed": True}
        self.assertEqual(
            transfer_evidence(self.pi, disputed, self.transfer, 90, "acct_partner")["state"],
            "charge_disputed"
        )

    def test_wrong_destination(self):
        self.assertEqual(transfer_evidence(self.pi, self.charge, self.transfer, 90, "acct_other")["state"], "destination_mismatch")

    def test_reversed(self):
        x = {**self.transfer, "amount_reversed": 1}
        self.assertEqual(transfer_evidence(self.pi, self.charge, x, 90, "acct_partner")["state"], "reversed_or_partially_reversed")

    def test_realistic_connected_account_with_overdue_verification_is_not_ready(self):
        disabled = {
            "metadata": {"partner_id": "partner-A"},
            "charges_enabled": False, "payouts_enabled": False,
            "capabilities": {"transfers": "inactive"},
            "requirements": {"currently_due": ["company.tax_id"], "disabled_reason": "requirements.past_due"},
        }
        result = connect_account_evidence(disabled, "partner-A")
        self.assertEqual(result["account_link_verified"], "verified")
        self.assertFalse(result["ready_for_partner_transfer"])
        self.assertTrue(result["requirements_pending"])
        self.assertEqual(result["disabled_reason"], "requirements.past_due")

    def test_active_account_with_correct_partner_is_ready(self):
        ready = {
            "metadata": {"partner_id": "partner-A"},
            "charges_enabled": True, "payouts_enabled": True,
            "capabilities": {"transfers": "active"},
            "requirements": {"currently_due": [], "disabled_reason": None},
        }
        self.assertTrue(connect_account_evidence(ready, "partner-A")["ready_for_partner_transfer"])
        self.assertFalse(connect_account_evidence(ready, "partner-B")["ready_for_partner_transfer"])

    def test_unlabelled_connected_account_is_not_auto_approved(self):
        ready_unlinked = {
            "metadata": {},
            "charges_enabled": True, "payouts_enabled": True,
            "capabilities": {"transfers": "active"},
            "requirements": {},
        }
        x = connect_account_evidence(ready_unlinked, "partner-A")
        self.assertEqual(x["account_link_verified"], "unverified")
        self.assertFalse(x["ready_for_partner_transfer"])



if __name__ == "__main__":
    unittest.main()
