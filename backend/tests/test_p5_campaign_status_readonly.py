"""Check no campaign status drift and read-only diagnostic rules."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADMIN = (ROOT / "backend/routes_admin.py").read_text()
SCRIPT = (ROOT / "scripts/rrclub_p5_campaigns_readonly.py").read_text()
source = ast.parse(SCRIPT)
names = {"percent_equal", "check_campaign", "summarize_campaigns"}
scope = {"Counter": __import__("collections").Counter, "date": __import__("datetime").date}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(ROOT / "scripts/rrclub_p5_campaigns_readonly.py"), "exec"), scope)

class CampaignStatusTests(unittest.TestCase):
    def test_default_campaign_status(self):
        self.assertIn('doc.setdefault("status", "Ativa" if kind == "campanhas" else "Ativo")', ADMIN)
        self.assertIn('if data.get("status") == "Ativo"', ADMIN)

    def test_rates_and_currency(self):
        c = {"status": "Ativa", "parceiro_id": "p", "influencer_id": "i", "desconto": 5, "comissao": 5}
        self.assertTrue(scope["check_campaign"](c, "eur", "2026-10-22")["p5_criteria_pass"])
        self.assertFalse(scope["check_campaign"]({**c, "status": "Ativo"}, "eur", "2026-10-22")["p5_criteria_pass"])
        self.assertFalse(scope["check_campaign"]({**c, "comissao": 10}, "brl", "2026-10-22")["p5_criteria_pass"])

    def test_diagnostic_does_not_modify_finances(self):
        for bad in ("update_one(", "insert_one(", "delete_one(", "stripe.Transfer.create(", "stripe.Account.modify("):
            self.assertNotIn(bad, SCRIPT)

if __name__ == "__main__":
    unittest.main()
