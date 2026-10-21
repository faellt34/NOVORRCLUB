"""Checkout MB WAY contract, without Stripe network, database or payment calls."""
import ast
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "p5_checkout.py").read_text(encoding="utf-8")

class DummyHTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

class DummyStripeInvalidRequestError(Exception):
    pass

class PortugalMbWayCheckoutTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_pt_stripe_checkout")
        function_module = ast.Module(body=[node], type_ignores=[])
        self.calls = []
        self.fail = False

        def fake_create(**kwargs):
            self.calls.append(kwargs)
            if self.fail:
                raise DummyStripeInvalidRequestError("mb_way unavailable")
            return SimpleNamespace(id="cs_placeholder", url="https://checkout.stripe.test/session")

        fake_stripe = SimpleNamespace(
            checkout=SimpleNamespace(Session=SimpleNamespace(create=fake_create)),
            error=SimpleNamespace(InvalidRequestError=DummyStripeInvalidRequestError),
        )
        scope = {"os": os, "stripe": fake_stripe, "HTTPException": DummyHTTPException}
        exec(compile(function_module, str(ROOT / "p5_checkout.py"), "exec"), scope)
        self.make_checkout = scope["_pt_stripe_checkout"]
        self.rec = {
            "id": "pc_p5_safe_mock", "campaign_id": "cmp_safe_mock",
            "partner_id": "part_safe_mock", "influencer_id": "inf_safe_mock",
            "coupon": "TEST-PT", "net_minor": 95,
            "commission_percent_snapshot": "5"
        }
        self.partner = {"nome": "Restaurante P5"}
        self.campaign = {"nome": "Campanha PT"}

    def do_checkout(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_unit_only"}):
            with patch.dict(sys.modules, {"pt_split": SimpleNamespace(automatic=lambda: True)}):
                return self.make_checkout(
                    self.rec, self.campaign, self.partner, "https://rrclub.online", None
                )

    def test_checkout_requests_mbway_and_card_same_session(self):
        session = self.do_checkout()
        self.assertEqual(session.id, "cs_placeholder")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["payment_method_types"], ["card", "mb_way"])
        self.assertEqual(self.calls[0]["line_items"][0]["price_data"]["currency"], "eur")
        self.assertEqual(self.calls[0]["line_items"][0]["price_data"]["unit_amount"], 95)

    def test_mbway_refusal_stops_without_card_only_charge(self):
        self.fail = True
        with self.assertRaises(DummyHTTPException) as raised:
            self.do_checkout()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("MB WAY", raised.exception.detail)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["payment_method_types"], ["card", "mb_way"])
        self.assertEqual(self.calls[0]["idempotency_key"], "p5-pc_p5_safe_mock-mbway")

if __name__ == "__main__":
    unittest.main()
