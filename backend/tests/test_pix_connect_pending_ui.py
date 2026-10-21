"""Pix association problems are distinct from Stripe unavailability."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIX = (ROOT / "routes_pix.py").read_text()
FRONT = (ROOT.parent / "frontend/src/pages/PartnerDashboard.jsx").read_text()
ONBOARD = (ROOT.parent / "frontend/src/components/PartnerOnboarding.jsx").read_text()
DIAGNOSTIC = (ROOT.parent / "scripts/rrclub_diagnose_partner_pix.py").read_text()


class PixConnectPendingUI(unittest.TestCase):
    def test_backend_pending_connection_is_not_500_or_payment(self):
        tree = ast.parse(PIX)
        route = next(x for x in tree.body if isinstance(x, ast.AsyncFunctionDef) and x.name == "connect_status")
        body = ast.unparse(route)
        self.assertIn("connect_brasil_associacao_pendente", body)
        self.assertIn("requires_admin_link", body)
        self.assertIn("status_verified", body)
        # Never create a new connected account or payment on status GET.
        for call in ("accounts.create", "transfers.create", "checkout.sessions.create"):
            self.assertNotIn(call, body)

    def test_frontend_display_reconciliation(self):
        self.assertIn("connect?.requires_admin_link", FRONT)
        self.assertIn("connect?.requires_admin_link", ONBOARD)

    def test_diagnostic_is_read_only(self):
        ast.parse(DIAGNOSTIC)
        for needle in ("update_one(", "insert_one(", "Account.modify(",
                       "Transfer.create(", "Account.create(", "Session.create("):
            self.assertNotIn(needle, DIAGNOSTIC)

if __name__ == "__main__":
    unittest.main()
