"""P5 activation: QR sessions don't require Stripe readiness, checkout still does."""
import ast
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


SOURCE = (Path(__file__).resolve().parents[1] / "p5_checkout.py").read_text()
TREE = ast.parse(SOURCE)
NAMES = {"enabled", "currency_enabled", "checkout_globally_enabled"}
PARTS = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
assert len(PARTS) == len(NAMES)
NAMESPACE = {"os": os}
exec(compile(ast.Module(body=PARTS, type_ignores=[]), "<p5-policy>", "exec"), NAMESPACE)


def config(**kwargs):
    env = {"P5_ENABLED": "true", "P5_EUR_ENABLED": "true",
           "P5_BRL_ENABLED": "true", "STRIPE_SECRET_KEY": "sk_live_unit_test"}
    env.update(kwargs)
    return env


class P5ActivationPolicyTest(unittest.TestCase):
    def test_off_by_default_and_opt_in(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(NAMESPACE["currency_enabled"]("eur"))
            self.assertFalse(NAMESPACE["currency_enabled"]("brl"))
        with patch.dict(os.environ, config()):
            self.assertTrue(NAMESPACE["currency_enabled"]("eur"))
            self.assertTrue(NAMESPACE["currency_enabled"]("brl"))
            self.assertFalse(NAMESPACE["currency_enabled"]("usd"))

    def test_pt_link_active_even_when_split_module_missing(self):
        with patch.dict(os.environ, config()):
            with patch.dict(sys.modules, {"pt_split": None}):
                self.assertTrue(NAMESPACE["currency_enabled"]("eur"))
                self.assertFalse(NAMESPACE["checkout_globally_enabled"]("eur"))

    def test_pt_payment_unavailable_when_live_split_disabled(self):
        with patch.dict(os.environ, config()):
            with patch.dict(sys.modules, {"pt_split": types.SimpleNamespace(automatic=lambda: False)}):
                self.assertTrue(NAMESPACE["currency_enabled"]("eur"))
                self.assertFalse(NAMESPACE["checkout_globally_enabled"]("eur"))

    def test_test_key_can_start_test_checkout_only(self):
        with patch.dict(os.environ, config(STRIPE_SECRET_KEY="sk_test_demo")):
            self.assertTrue(NAMESPACE["checkout_globally_enabled"]("eur"))

    def test_br_link_active_when_pix_provider_not_ready(self):
        fake_pix = types.SimpleNamespace(availability_configuration=lambda: ({"accepting_new_payments": False}, {}))
        with patch.dict(os.environ, config()):
            with patch.dict(sys.modules, {"routes_pix": fake_pix}):
                self.assertTrue(NAMESPACE["currency_enabled"]("brl"))
                self.assertFalse(NAMESPACE["checkout_globally_enabled"]("brl"))

    def test_no_transfer_created_by_qr_config(self):
        # Read-only flag functions must not contain any payment or transfer calls.
        for node in PARTS:
            names = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            self.assertFalse({"create", "Transfer", "PaymentIntent", "Session"} & names)
        self.assertIn("await wait_for_connect(rec", SOURCE)
        self.assertIn('"status": "awaiting_connect"', SOURCE)


if __name__ == "__main__":
    unittest.main()
