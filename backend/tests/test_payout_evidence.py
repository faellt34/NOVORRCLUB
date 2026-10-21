import unittest

from payout_attribution import payout_evidence, payout_status


class PayoutEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rec = {
            "campaign_id": "c1", "partner_id": "p1", "influencer_id": "i1",
            "coupon": "RR-EXAMPLE", "paid_online": True, "idempotency_key": "cs_paid_1"
        }
        self.campaigns = {"c1": {"id": "c1", "influencer_id": "i1"}}
        self.influencers = {"i1": {"id": "i1", "nome": "Exemplo"}}
        self.paid = {"cs_paid_1": {"session_id": "cs_paid_1", "payment_status": "paid",
                                   "campaign_id": "c1", "partner_id": "p1", "coupon": "RR-EXAMPLE"}}

    def check(self, record=None, campaigns=None, influencers=None, paid=None):
        return payout_evidence(record if record is not None else self.rec,
                               campaigns if campaigns is not None else self.campaigns,
                               influencers if influencers is not None else self.influencers,
                               paid if paid is not None else self.paid)

    def test_fully_attributed_paid_payment(self):
        self.assertIsNone(self.check())
        self.assertEqual(payout_status([], False), "Pendente")

    def test_missing_influencer_id(self):
        self.assertEqual(self.check(record={**self.rec, "influencer_id": None}), "beneficiary_id_missing")
        self.assertEqual(payout_status(["beneficiary_id_missing"]), "Atribuição por confirmar")

    def test_unregistered_influencer(self):
        self.assertEqual(self.check(influencers={}), "beneficiary_not_registered")

    def test_campaign_beneficiary_mismatch(self):
        self.assertEqual(self.check(campaigns={"c1": {"id": "c1", "influencer_id": "i2"}}),
                         "campaign_beneficiary_mismatch")

    def test_manual_redemption_does_not_count_as_stripe_payment(self):
        self.assertEqual(self.check(record={**self.rec, "paid_online": False}),
                         "manual_redemption_requires_payment_proof")
        self.assertEqual(payout_status(["manual_redemption_requires_payment_proof"]), "Pagamento por confirmar")

    def test_pending_stripe_session(self):
        self.assertEqual(self.check(paid={}), "stripe_payment_not_confirmed")
        self.assertEqual(self.check(paid={"cs_paid_1": {**self.paid["cs_paid_1"], "payment_status": "pending"}}),
                         "stripe_payment_not_confirmed")

    def test_payment_of_another_campaign_does_not_validate_payout(self):
        self.assertEqual(self.check(paid={"cs_paid_1": {**self.paid["cs_paid_1"], "campaign_id": "other"}}),
                         "stripe_payment_campaign_mismatch")

    def test_payment_of_another_partner_does_not_validate_payout(self):
        self.assertEqual(self.check(paid={"cs_paid_1": {**self.paid["cs_paid_1"], "partner_id": "other"}}),
                         "stripe_payment_campaign_mismatch")

    def test_payment_of_another_coupon_does_not_validate_payout(self):
        self.assertEqual(self.check(paid={"cs_paid_1": {**self.paid["cs_paid_1"], "coupon": "other"}}),
                         "stripe_payment_campaign_mismatch")

    def test_historical_paid_declaration_remains_visible_without_claiming_bank_evidence(self):
        self.assertEqual(payout_status(["manual_redemption_requires_payment_proof"], True), "Pago")


if __name__ == "__main__":
    unittest.main()
