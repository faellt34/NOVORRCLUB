import unittest
from p5_rules import quote_minor, P5QuoteError


class P5PriceTest(unittest.TestCase):
    def test_portugal_100_bill_10_discount_is_90_eur(self):
        q = quote_minor("100.00", "10", "5", "eur")
        self.assertEqual((q["gross_minor"], q["discount_minor"], q["net_minor"]), (10000, 1000, 9000))

    def test_brazil_100_bill_5_percent_is_95_brl(self):
        q = quote_minor("100.00", "5", "5", "brl")
        self.assertEqual((q["gross_minor"], q["discount_minor"], q["net_minor"]), (10000, 500, 9500))
        self.assertEqual(q["commission_percent_snapshot"], "5")

    def test_cents_rounded_half_up(self):
        q = quote_minor("17.15", "10", "5", "eur")
        self.assertEqual(q["gross_minor"], 1715)
        self.assertEqual(q["discount_minor"], 172)
        self.assertEqual(q["net_minor"], 1543)

    def test_rejects_brazil_wrong_rate(self):
        with self.assertRaises(P5QuoteError):
            quote_minor("100", "10", "5", "brl")
        with self.assertRaises(P5QuoteError):
            quote_minor("100", "5", "10", "brl")

    def test_rejects_malicious_or_invalid_input(self):
        for bad in ("NaN", "Infinity", "-1", "0", "10001"):
            with self.subTest(bad=bad), self.assertRaises(P5QuoteError):
                quote_minor(bad, "10", "5", "eur")
        for bad in ("NaN", "Infinity", "100", "-1"):
            with self.subTest(bad=bad), self.assertRaises(P5QuoteError):
                quote_minor("100", bad, "5", "eur")

    def test_does_not_derive_amount_from_browser_after_quote(self):
        q = quote_minor("100", 5, 5, "brl")
        self.assertNotIn("origin_url", q)
        self.assertNotIn("payment_status", q)
        self.assertNotIn("transfer_status", q)


if __name__ == "__main__":
    unittest.main()
