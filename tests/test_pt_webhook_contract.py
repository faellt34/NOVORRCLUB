"""Read-only regression checks for the Portugal P5 webhook control flow.

Run from repo root: python -m unittest discover -s tests -p 'test_pt_webhook_contract.py'
No network, no Stripe credentials, no real payments.
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYMENTS = ROOT / "backend" / "routes_payments.py"
SPLIT = ROOT / "backend" / "pt_split.py"

class PortugalP5WebhookContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payments = ast.parse(PAYMENTS.read_text(encoding="utf-8"))
        cls.split = ast.parse(SPLIT.read_text(encoding="utf-8"))

    def test_webhook_has_finally_guard_for_financial_settlement(self):
        func = next(n for n in self.payments.body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "stripe_webhook")
        guarded = [n for n in ast.walk(func) if isinstance(n, ast.Try)
                   and any(isinstance(x, ast.Await)
                           and isinstance(x.value, ast.Call)
                           and isinstance(x.value.func, ast.Name)
                           and x.value.func.id == "fulfil"
                           for s in n.body for x in ast.walk(s))]
        self.assertEqual(len(guarded), 1, "Exactly one protected fulfilment block expected")
        final_calls = [x.value.func.id for s in guarded[0].finalbody
                       for x in ast.walk(s)
                       if isinstance(x, ast.Await) and isinstance(x.value, ast.Call)
                       and isinstance(x.value.func, ast.Name)]
        self.assertIn("settle_webhook_safely", final_calls)

    def test_transfer_is_guarded_by_ready_recipients(self):
        func = next(n for n in self.split.body
                    if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "settle_new_p5_payment")
        source = ast.get_source_segment(SPLIT.read_text(encoding="utf-8"), func) or ""
        self.assertIn("recipients_ready", source)
        self.assertIn("beneficiary_account_not_ready_or_changed", source)
        self.assertIn("stripe_payment_or_transfer_not_verified", source)

    def test_split_requires_explicit_activation(self):
        names = {n.name: n for n in self.split.body if isinstance(n, ast.FunctionDef)}
        self.assertIn("automatic", names)
        code = ast.get_source_segment(SPLIT.read_text(encoding="utf-8"), names["automatic"]) or ""
        self.assertIn("PT_SPLIT_AUTO_TRANSFER", code)

if __name__ == "__main__":
    unittest.main()
