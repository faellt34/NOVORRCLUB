import unittest
from p5_quote import quote, QuoteError

class QuoteTests(unittest.TestCase):
    def test_pt(self):
        q = quote("100", "10", "PT")
        self.assertEqual((q["currency"], q["discount"], q["payable"]), ("eur", "10.00", "90.00"))
        self.assertIn("mb_way", q["candidate_methods"])
        self.assertNotIn("pix", q["candidate_methods"])
    def test_br(self):
        q = quote("100", 10, "BR")
        self.assertEqual((q["currency"], q["payable"]), ("brl", "90.00"))
        self.assertIn("pix", q["candidate_methods"])
        self.assertNotIn("mb_way", q["candidate_methods"])
    def test_rounding(self):
        self.assertEqual(quote("7.11", 5, "PT")["payable"], "6.75")
    def test_invalid(self):
        for amount, pct, country in [("NaN", 10, "PT"), (-1, 10, "BR"),
                                     (100, -1, "PT"), (100, 101, "BR"),
                                     (100, 10, "US"), (100, 100, "PT")]:
            with self.subTest(value=(amount, pct, country)), self.assertRaises(QuoteError):
                quote(amount, pct, country)

if __name__ == "__main__":
    unittest.main()
