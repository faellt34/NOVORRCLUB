import unittest
from p5_cash_rules import CashRuleError, quote_cash, confirm_cash


class P5CashRulesTests(unittest.TestCase):
    def test_euro(self):
        q = quote_cash("100", "5", "10", "EUR")
        self.assertEqual((q["discount"], q["payable"], q["commission_owed"]), ("5.00", "95.00", "10.00"))
        self.assertEqual(q["payment_status"], "pending_cash")
        self.assertEqual(q["stripe_status"], "not_applicable")

    def test_brazil(self):
        q = quote_cash("20.00", 5, 10, "brl")
        self.assertEqual((q["payable"], q["currency"]), ("19.00", "brl"))

    def test_rounding(self):
        q = quote_cash("7.11", "5", "10")
        self.assertEqual((q["discount"], q["payable"], q["commission_owed"]), ("0.36", "6.75", "0.71"))

    def test_confirm_authorized(self):
        self.assertEqual(confirm_cash("pending_cash", True, True, True), "cash_confirmed_by_partner")

    def test_duplicate_not_allowed(self):
        with self.assertRaises(CashRuleError):
            confirm_cash("cash_confirmed_by_partner", True, True, True)

    def test_pending_money(self):
        with self.assertRaises(CashRuleError):
            confirm_cash("pending_cash", False, True, True)

    def test_foreign_partner(self):
        with self.assertRaises(CashRuleError):
            confirm_cash("pending_cash", True, True, False)

    def test_unauthorized(self):
        with self.assertRaises(CashRuleError):
            confirm_cash("pending_cash", True, False, True)

    def test_invalid_value(self):
        for x in ("nan", "-1", "10001", "abc", "Infinity"):
            with self.subTest(x=x), self.assertRaises(CashRuleError):
                quote_cash(x, 5, 10)

    def test_invalid_currency(self):
        with self.assertRaises(CashRuleError):
            quote_cash("20", 5, 10, "usd")

    def test_invalid_percent(self):
        with self.assertRaises(CashRuleError):
            quote_cash("20", 110, 10)

    def test_commission_over_net(self):
        with self.assertRaises(CashRuleError):
            quote_cash("20", 90, 30)


if __name__ == "__main__":
    unittest.main()
