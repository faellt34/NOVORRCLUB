import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LegacyCampaignCompatibility(unittest.TestCase):
    def test_coupon_payload_contains_campaign_level_p5_eligibility(self):
        s = (ROOT / "routes_data.py").read_text()
        self.assertIn('"p5_eligible": p5_eligible', s)
        self.assertIn('float(c.get("desconto", -1)) == 5', s)
        self.assertIn('float(c.get("comissao", -1)) == 5', s)

    def test_old_eur_checkout_not_blocked_for_other_percentages(self):
        s = (ROOT / "routes_payments.py").read_text()
        self.assertIn('if currency_enabled("eur") and float(c.get("desconto", -1)) == 5', s)

    def test_p5_rejects_unsupported_campaign_before_session_creation(self):
        s = (ROOT / "p5_checkout.py").read_text()
        self.assertIn('Esta campanha usa o fluxo de cupão habitual', s)
        # Structural syntax check without database or Stripe imports.
        for file in ("routes_data.py", "routes_payments.py", "p5_checkout.py"):
            ast.parse((ROOT / file).read_text(), filename=file)


if __name__ == "__main__":
    unittest.main()
