"""Campaign audit and admin status normalization; no Mongo/Stripe access."""
import ast
from collections import Counter
from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "scripts/rrclub_p5_campaigns_readonly.py").read_text()
TREE = ast.parse(SOURCE)
NEEDED = {"percent_equal", "check_campaign", "summarize_campaigns"}
PURE = ast.Module(
    body=[n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in NEEDED],
    type_ignores=[],
)
scope = {"date": date, "Counter": Counter}
exec(compile(PURE, "<P5 pure audit>", "exec"), scope)


class CampaignStatusAudit(unittest.TestCase):
    def test_campaign_creation_default_is_Ativa_and_not_for_partners(self):
        source = (ROOT / "backend/routes_admin.py").read_text()
        self.assertIn('"Ativa" if kind == "campanhas" else "Ativo"', source)
        self.assertIn('if data.get("status") == "Ativo":', source)

    def test_missing_and_legacy_status_are_reported_not_migrated(self):
        c = {"id": "c1", "status": "Ativo", "parceiro_id": "p1", "influencer_id": "i1",
             "desconto": 5, "comissao": 5, "currency": "eur", "validade": "2030-12-31"}
        result = scope["check_campaign"](c, today="2026-10-22")
        self.assertEqual(result["reasons"], ["status_not_Ativa"])
        self.assertEqual(c["status"], "Ativo")

    def test_legacy_rates_do_not_silently_enter_p5(self):
        c = {"status": "Ativa", "parceiro_id": "p1", "influencer_id": "i1",
             "desconto": 10, "comissao": 10, "validade": "2030-12-31"}
        summary = scope["summarize_campaigns"]([c], {"p1": "brl"}, "2026-10-22")
        self.assertEqual(summary["p5_eligible_by_country"]["brl"], 0)
        self.assertEqual(summary["p5_exclusion_reasons"]["discount_not_5"], 1)
        self.assertEqual(summary["p5_exclusion_reasons"]["commission_not_5"], 1)

    def test_active_p5_per_country_with_legacy_currency(self):
        first = {"id": "pt", "status": "Ativa", "parceiro_id": "p1", "influencer_id": "i1",
                 "desconto": "5,0", "comissao": "5", "validade": "2030-12-31"}
        second = dict(first, id="br", parceiro_id="p2", currency="brl")
        summary = scope["summarize_campaigns"]([first, second],
                                                {"p1": "eur", "p2": "brl"}, "2026-10-22")
        self.assertEqual(summary["p5_eligible_by_country"], {"brl": 1, "eur": 1})
        self.assertEqual(summary["campaigns_checked"], 2)

    def test_expired_campaign_not_financially_eligible(self):
        c = {"status": "Ativa", "parceiro_id": "p1", "influencer_id": "i1",
             "desconto": 5, "comissao": 5, "currency": "eur", "validade": "2020-01-01"}
        self.assertIn("campaign_expired", scope["check_campaign"](c, today="2026-10-22")["reasons"])

    def test_read_only(self):
        for forbidden in ("update_one(", "insert_one(", "delete_one(", "replace_one(",
                          "Transfer.create(", "Account.modify(", "Session.create("):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
