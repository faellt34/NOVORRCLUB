"""Read-only account labels must never become beneficiary evidence."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "pt_split.py").read_text()
SCRIPT = (ROOT.parent / "scripts/rrclub_pt_live_eligibility_audit.py").read_text()

class PTAccountAliasesTests(unittest.TestCase):
    def test_known_account_aliases(self):
        self.assertIn('acct_1UIajlE123roTruk', SOURCE)
        self.assertIn('acct_1UIacdCy6KhbVjNX', SOURCE)
        self.assertIn('Conta PT-01', SOURCE)
        self.assertIn('Conta PT-02', SOURCE)

    def test_endpoint_read_only_and_admin_guard(self):
        tree = ast.parse(SOURCE)
        node = next(x for x in tree.body if isinstance(x, ast.AsyncFunctionDef) and x.name == "pt_accounts_inventory")
        self.assertIn('require_role("admin")', ast.unparse(node.args))
        calls = [ast.unparse(x.func) for x in ast.walk(node) if isinstance(x, ast.Call)]
        self.assertNotIn('stripe.Transfer.create', calls)
        self.assertFalse(any(x.startswith('stripe.Account.modify') for x in calls))
        self.assertFalse(any(x.endswith(('update_one', 'insert_one', 'replace_one', 'delete_one')) for x in calls))
        self.assertIn('aliases_are_not_beneficiary_ids', ast.unparse(node))

    def test_empty_lists_are_explained(self):
        ast.parse(SCRIPT)
        self.assertIn('wrong_stripe_account', SCRIPT)
        self.assertIn('active_campaigns_in_db', SCRIPT)
        self.assertIn('connected_candidates.append(item)', SCRIPT)

if __name__ == '__main__':
    unittest.main()
