import unittest
from finance_evidence import transfer_evidence


class FinancialEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.intent = {"status": "succeeded", "amount": 900}
        self.charge = {"transfer": "tr_live_example"}
        self.transfer = {"id": "tr_live_example", "destination": "acct_partner_example",
                         "amount": 850, "amount_reversed": 0, "reversed": False, "currency": "eur"}

    def verify(self, **kwargs):
        return transfer_evidence(self.intent, self.charge, self.transfer, 900,
                                 "acct_partner_example", **kwargs)

    def test_transfer_is_not_bank_payout(self):
        r = self.verify()
        self.assertEqual(r["state"], "transferred_to_connected_stripe_account")
        self.assertEqual(r["bank_payout"], "not_verified")

    def test_paid_payment_is_not_transfer(self):
        r = transfer_evidence(self.intent, None, None, 900, "acct_partner_example")
        self.assertEqual(r["state"], "no_transfer_evidence")

    def test_wrong_amount_is_blocked(self):
        r = transfer_evidence(self.intent, self.charge, self.transfer, 1000, "acct_partner_example")
        self.assertEqual(r["state"], "amount_mismatch")

    def test_wrong_destination_is_blocked(self):
        r = transfer_evidence(self.intent, self.charge, self.transfer, 900, "acct_other")
        self.assertEqual(r["state"], "destination_mismatch")

    def test_missing_partner_link_is_blocked(self):
        r = transfer_evidence(self.intent, self.charge, self.transfer, 900, None)
        self.assertEqual(r["state"], "destination_unlinked")

    def test_reversal_is_not_confirmed(self):
        t = {**self.transfer, "amount_reversed": 250}
        r = transfer_evidence(self.intent, self.charge, t, 900, "acct_partner_example")
        self.assertEqual(r["state"], "reversed_or_partially_reversed")

    def test_failed_payment_is_not_transfer(self):
        r = transfer_evidence({"status": "requires_payment_method", "amount": 900},
                              self.charge, self.transfer, 900, "acct_partner_example")
        self.assertEqual(r["state"], "payment_not_succeeded")


if __name__ == "__main__":
    unittest.main()
