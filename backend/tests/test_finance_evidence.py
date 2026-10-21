import unittest
from finance_evidence import transfer_evidence


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

    def test_wrong_destination(self):
        self.assertEqual(transfer_evidence(self.pi, self.charge, self.transfer, 90, "acct_other")["state"], "destination_mismatch")

    def test_reversed(self):
        x = {**self.transfer, "amount_reversed": 1}
        self.assertEqual(transfer_evidence(self.pi, self.charge, x, 90, "acct_partner")["state"], "reversed_or_partially_reversed")


if __name__ == "__main__":
    unittest.main()
