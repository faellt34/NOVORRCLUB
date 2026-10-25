"""Regressões mínimas: P5 verdadeiro versus históricos/testes, por moeda."""
import unittest

from diretor_estrategia import amounts_minor, financial_state, is_new_p5, is_synthetic


def br_payment(**overrides):
    tx = {
        "kind": "pix_coupon", "currency": "brl",
        "split_version": "br-fixed-5-80-5-10-v1", "payment_status": "paid",
        "gross_cents": 10000, "net_cents": 9500,
        "partner_cents": 8000, "influencer_cents": 500, "platform_cents": 1000,
        "split_status": "pending",
    }
    tx.update(overrides)
    return tx


def pt_payment(**overrides):
    tx = {
        "kind": "coupon_pay", "currency": "eur", "p5_charge_id": "charge-1",
        "split_version": "pt-p5-fixed-5-80-5-10-v1", "gross_minor": 10000, "amount": 95,
        "partner_minor": 8000, "influencer_minor": 500, "platform_minor": 1000,
        "payment_status": "paid", "pt_split_status": "pending",
    }
    tx.update(overrides)
    return tx


class VerifiedDirectorTests(unittest.TestCase):
    def test_legacy_coupon_not_p5(self):
        tx = pt_payment(p5_charge_id=None)
        self.assertFalse(is_new_p5(tx, "eur"))
        self.assertEqual(financial_state(tx, "eur"), "fora_p5")

    def test_incompatible_portugal_version_rejected(self):
        self.assertFalse(is_new_p5(pt_payment(split_version="legacy"), "eur"))

    def test_currency_separation(self):
        self.assertFalse(is_new_p5(br_payment(), "eur"))
        self.assertFalse(is_new_p5(pt_payment(), "brl"))

    def test_stripe_test_mode_excluded(self):
        self.assertFalse(is_new_p5(br_payment(livemode=False), "brl"))

    def test_simulation_excluded(self):
        tx = br_payment(is_test=True)
        self.assertTrue(is_synthetic(tx))
        self.assertFalse(is_new_p5(tx, "brl"))

    def test_unpaid_is_not_revenue(self):
        self.assertEqual(financial_state(br_payment(payment_status="pending"), "brl"), "aguarda_pagamento")

    def test_refund_or_dispute_held(self):
        self.assertEqual(financial_state(br_payment(refunded_cents=500), "brl"), "reembolso_a_conciliar")
        self.assertEqual(financial_state(pt_payment(dispute_hold=True), "eur"), "em_disputa")

    def test_paid_not_bank_payout(self):
        self.assertEqual(financial_state(pt_payment(), "eur"), "pago_repasses_pendentes")
        self.assertEqual(financial_state(br_payment(), "brl"), "pago_repasses_pendentes")

    def test_connect_ids_required(self):
        tx = br_payment(split_status="completed", partner_transfer_id="tr_1")
        self.assertEqual(financial_state(tx, "brl"), "pago_repasses_pendentes")
        tx["influencer_transfer_id"] = "tr_2"
        self.assertEqual(financial_state(tx, "brl"), "transferido_connect")

    def test_splits_are_exact_and_not_tax_estimations(self):
        self.assertEqual(amounts_minor(br_payment(), "brl"),
            {"bruto": 10000, "cobrado": 9500, "parceiro": 8000, "influenciador": 500, "rrclub": 1000})
        self.assertEqual(amounts_minor(pt_payment(), "eur")["cobrado"], 9500)
        self.assertIsNone(amounts_minor(br_payment(platform_cents=1100), "brl"))


if __name__ == "__main__":
    unittest.main()
