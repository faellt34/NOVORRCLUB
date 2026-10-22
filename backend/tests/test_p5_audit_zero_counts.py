"""Regression tests: P5 report must not imply a missing campaign from zero P5 count."""
import ast
from datetime import datetime, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "scripts/rrclub_p5_accounts_br_pt_readonly.py").read_text()
TREE = ast.parse(SRC)
FN = next(n for n in TREE.body if isinstance(n, ast.FunctionDef)
          and n.name == "campaign_exclusion_reasons")
SCOPE = {}
exec(compile(ast.Module(body=[FN], type_ignores=[]), "<pure audit>", "exec"), SCOPE)
reasons = SCOPE["campaign_exclusion_reasons"]


class ZeroCountsTests(unittest.TestCase):
    def test_legacy_status_explained(self):
        c = {"status": "Ativo", "parceiro_id": "p", "influencer_id": "i",
             "desconto": 5, "comissao": 5}
        self.assertEqual(reasons(c, "2026-10-22"), ["status_not_Ativa"])

    def test_different_rates_explained_not_modified(self):
        c = {"status": "Ativa", "parceiro_id": "p", "influencer_id": "i",
             "desconto": 10, "comissao": 7}
        self.assertEqual(reasons(c, "2026-10-22"),
                         ["discount_not_5", "commission_not_5"])
        self.assertEqual(c["comissao"], 7)

    def test_expired_campaign(self):
        c = {"status": "Ativa", "parceiro_id": "p", "influencer_id": "i",
             "desconto": 5, "comissao": 5, "validade": "2025-01-01"}
        self.assertEqual(reasons(c, "2026-10-22"), ["expired"])

    def test_valid_campaign(self):
        c = {"status": "Ativa", "parceiro_id": "p", "influencer_id": "i",
             "desconto": 5, "comissao": 5, "validade": "2028-01-01"}
        self.assertEqual(reasons(c, "2026-10-22"), [])

    def test_missing_ids(self):
        c = {"status": "Ativa", "desconto": 5, "comissao": 5}
        self.assertEqual(reasons(c, "2026-10-22"),
                         ["missing_partner_id", "missing_influencer_id"])

    def test_report_separates_total_and_p5_and_infers_currency(self):
        self.assertIn('total = await db.campaigns.count_documents({})', SRC)
        self.assertIn('legacy_active = await db.campaigns.count_documents({"status": "Ativo"})', SRC)
        self.assertIn('campaign.get("currency") or partner.get("currency") or "eur"', SRC)
        self.assertIn('"exclusion_reasons_sample"', SRC)
        self.assertIn('"needs_additional_recipient_checks": True', SRC)

    def test_read_only(self):
        for forbidden in ("update_one(", "insert_one(", "delete_one(",
                          "Transfer.create(", "Account.modify(", "Session.create("):
            self.assertNotIn(forbidden, SRC)


if __name__ == "__main__":
    unittest.main()
