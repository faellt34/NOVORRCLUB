"""Unit-test pure P5 audit policy without Stripe/Mongo/network."""
import ast
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/rrclub_p5_accounts_br_pt_readonly.py"
SRC = SCRIPT.read_text(encoding="utf-8")
TREE = ast.parse(SRC)
FUNCTIONS = (
    "verified_financial_capability",
    "exact_metadata_binding",
    "p5_policy_campaign",
)
SCOPE = {}
exec(compile(ast.Module(
    body=[node for node in TREE.body
          if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS],
    type_ignores=[]), str(SCRIPT), "exec"), SCOPE)


class P5AccountAuditTests(unittest.TestCase):
    def setUp(self):
        self.account = {
            "id": "acct_test_brl", "country": "BR", "payouts_enabled": True,
            "capabilities": {"transfers": "active"},
            "settings": {"payouts": {"schedule": {"interval": "daily"}}},
            "requirements": {"currently_due": [], "past_due": [], "disabled_reason": None},
            "metadata": {"partner_id": "part_123"},
        }
        self.entity = {"id": "part_123", "pix_stripe_account_id": "acct_test_brl"}

    def test_financially_capable_does_not_mean_id_matched(self):
        self.assertTrue(SCOPE["verified_financial_capability"](self.account, "BR"))
        self.assertFalse(SCOPE["verified_financial_capability"](self.account, "PT"))
        self.assertFalse(SCOPE["exact_metadata_binding"](
            self.account, {"id": "part_999", "pix_stripe_account_id": "acct_test_brl"},
            "acct_test_brl", "pix_stripe_account_id", "partner"))
        self.assertTrue(SCOPE["exact_metadata_binding"](
            self.account, self.entity, "acct_test_brl", "pix_stripe_account_id", "partner"))

    def test_missing_or_conflicting_metadata_is_not_identity_evidence(self):
        other = dict(self.account)
        other["metadata"] = {}
        self.assertFalse(SCOPE["exact_metadata_binding"](
            other, self.entity, "acct_test_brl", "pix_stripe_account_id", "partner"))
        other["metadata"] = {"partner_id": "part_123", "influencer_id": "inf_wrong"}
        self.assertFalse(SCOPE["exact_metadata_binding"](
            other, self.entity, "acct_test_brl", "pix_stripe_account_id", "partner"))

    def test_expired_financial_capability_not_assumed(self):
        blocked = dict(self.account)
        blocked["requirements"] = {"currently_due": ["individual.verification.document"]}
        self.assertFalse(SCOPE["verified_financial_capability"](blocked, "BR"))
        blocked = dict(self.account)
        blocked["payouts_enabled"] = False
        self.assertFalse(SCOPE["verified_financial_capability"](blocked, "BR"))

    def test_campaign_requires_both_p5_roles(self):
        base = {"desconto": 5, "comissao": 5, "parceiro_id": "p1", "influencer_id": "i1"}
        self.assertTrue(SCOPE["p5_policy_campaign"](base))
        self.assertFalse(SCOPE["p5_policy_campaign"]({**base, "influencer_id": None}))
        self.assertFalse(SCOPE["p5_policy_campaign"]({**base, "comissao": 10}))

    def test_no_mutations_or_kcv_credential_logging(self):
        forbidden = ("update_one(", "insert_one(", "delete_one(", "replace_one(",
                     "Transfer.create(", "Session.create(", "Account.modify(",
                     "Account.create(", "metadata.update(")
        for operation in forbidden:
            self.assertNotIn(operation, SRC)
        self.assertNotIn("password_hash", SRC)
        self.assertNotIn("api_key\": key", SRC)
        self.assertIn("read_only", SRC)


if __name__ == "__main__":
    unittest.main()
