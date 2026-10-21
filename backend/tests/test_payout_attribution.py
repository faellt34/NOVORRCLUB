import unittest
from payout_attribution import payout_evidence, payout_status


class AttributionTest(unittest.TestCase):
    def setUp(self):
        self.r = {"campaign_id": "c1", "partner_id": "p1", "influencer_id": "i1",
                  "coupon": "R-EXAMPLE", "idempotency_key": "cs_paid_1", "paid_online": True}
        self.camps = {"c1": {"influencer_id": "i1"}}
        self.infs = {"i1": {"nome": "Exemplo"}}
        self.tx = {"cs_paid_1": {"payment_status": "paid", "kind": "coupon_pay",
                                "campaign_id": "c1", "partner_id": "p1", "coupon": "R-EXAMPLE",
                                "influencer_id": "i1"}}

    def check(self, rec=None, tx=None, camps=None, infs=None):
        return payout_evidence(self.r if rec is None else rec,
                               self.camps if camps is None else camps,
                               self.infs if infs is None else infs,
                               self.tx if tx is None else tx)

    def test_reconciled(self):
        self.assertIsNone(self.check())
        self.assertEqual(payout_status([], False), "Pendente")

    def test_no_influencer(self):
        self.assertEqual(self.check(rec={**self.r, "influencer_id": None}), "beneficiary_id_missing")
        self.assertEqual(payout_status(["beneficiary_id_missing"]), "Atribuição por confirmar")

    def test_wrong_campaign(self):
        self.assertEqual(self.check(camps={"c1": {"influencer_id": "i2"}}),
                         "campaign_beneficiary_mismatch")

    def test_manual_does_not_prove_money(self):
        self.assertEqual(self.check(rec={**self.r, "paid_online": False}),
                         "manual_redemption_requires_payment_proof")
        self.assertEqual(payout_status(["manual_redemption_requires_payment_proof"]),
                         "Pagamento por confirmar")

    def test_unpaid_session(self):
        self.assertEqual(self.check(tx={}), "stripe_payment_not_confirmed")

    def test_legacy_checkout_cannot_allocate_commission_without_frozen_beneficiary(self):
        old = {**self.tx["cs_paid_1"]}
        old.pop("influencer_id")
        self.assertEqual(
            self.check(tx={"cs_paid_1": old}), "checkout_beneficiary_not_verified"
        )

    def test_checkout_snapshot_mismatch(self):
        altered = {**self.tx["cs_paid_1"], "influencer_id": "other"}
        self.assertEqual(
            self.check(tx={"cs_paid_1": altered}), "checkout_beneficiary_not_verified"
        )

    def test_wrong_partner(self):
        self.assertEqual(self.check(tx={"cs_paid_1": {**self.tx["cs_paid_1"], "partner_id": "p2"}}),
                         "stripe_payment_campaign_mismatch")

    def test_dispute(self):
        self.assertEqual(self.check(rec={**self.r, "dispute_hold": True}),
                         "payment_disputed_or_refunded")

    def test_manual_record_remains_visible(self):
        self.assertEqual(payout_status(["manual_redemption_requires_payment_proof"], True), "Pago")


if __name__ == "__main__":
    unittest.main()
