import os
import unittest
from unittest.mock import patch

from pt_split import quote, cents, VERSION, live_enabled, automatic
from p5_rules import quote_minor, P5QuoteError


class PortugalSplitContract(unittest.TestCase):
    def test_100_eur_gross_exact_contract(self):
        q = quote(10000)
        self.assertEqual(q["discount_minor"], 500)
        self.assertEqual(q["payment_minor"], 9500)
        self.assertEqual(q["partner_minor"], 8000)
        self.assertEqual(q["influencer_minor"], 500)
        self.assertEqual(q["platform_minor"], 1000)
        self.assertEqual(q["version"], VERSION)
        self.assertEqual(q["stripe_fees_borne_by"], "platform")

    def test_rounding_preserves_exact_paid_total(self):
        for gross in (100, 101, 119, 199, 201, 999, 1715, 10000, 1000000):
            q = quote(gross)
            self.assertEqual(sum(q[k] for k in ("partner_minor", "influencer_minor", "platform_minor")), q["payment_minor"])
            self.assertEqual(q["gross_minor"] - q["discount_minor"], q["payment_minor"])
            self.assertGreaterEqual(q["platform_minor"], 0)

    def test_bad_amounts_fail_closed(self):
        for bad in (-1, 0, 30, 99, 1000001, True, "10000"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                quote(bad)
        for bad in ("NaN", "Infinity", "a", None):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                cents(bad)

    def test_pt_and_br_have_same_fixed_percentage_contract(self):
        for c in ("eur", "brl"):
            q = quote_minor("100.00", "5", "5", c)
            self.assertEqual((q["gross_minor"], q["discount_minor"], q["net_minor"]), (10000, 500, 9500))
            with self.assertRaises(P5QuoteError):
                quote_minor("100.00", "10", "5", c)

    def test_live_transfer_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(live_enabled())
            self.assertFalse(automatic())
        with patch.dict(os.environ, {"PT_SPLIT_ENABLED": "true", "PT_SPLIT_LIVE_ENABLED": "true"}, clear=True):
            self.assertTrue(live_enabled())
            self.assertFalse(automatic())
        with patch.dict(os.environ, {"PT_SPLIT_ENABLED": "true", "PT_SPLIT_LIVE_ENABLED": "true", "PT_SPLIT_AUTO_TRANSFER": "true"}, clear=True):
            self.assertTrue(automatic())

    def test_not_a_declaration_of_bank_payout(self):
        q = quote(10000)
        self.assertNotIn("bank_payout", q)
        self.assertNotIn("bank_payout_verified", q)
        self.assertNotIn("transfer_id", q)
        self.assertNotIn("payment_status", q)


if __name__ == "__main__":
    unittest.main()
