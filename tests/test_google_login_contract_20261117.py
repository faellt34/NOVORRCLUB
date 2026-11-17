"""Read-only structural regression checks for the RRClub Google login flow.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_google_login_contract_20261117.py'

These checks validate source contracts only. They do not prove OAuth works
against Google, that the frontend builds, or that Emergent is deployed.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GoogleLoginContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth = (ROOT / "backend/routes_auth.py").read_text(encoding="utf-8")
        cls.identity = (ROOT / "backend/google_identity.py").read_text(encoding="utf-8")
        cls.button = (ROOT / "frontend/src/components/GoogleSignIn.jsx").read_text(encoding="utf-8")
        cls.login = (ROOT / "frontend/src/pages/Login.jsx").read_text(encoding="utf-8")
        cls.register = (ROOT / "frontend/src/pages/Register.jsx").read_text(encoding="utf-8")
        cls.app = (ROOT / "frontend/src/App.js").read_text(encoding="utf-8")

    def test_backend_modules_parse(self):
        ast.parse(self.auth, filename="backend/routes_auth.py")
        ast.parse(self.identity, filename="backend/google_identity.py")

    def test_google_endpoints_and_nonce_challenge(self):
        for fragment in ('@router.get("/google/config")', '@router.post("/google")',
                         '@router.post("/google/link")', 'google_challenges',
                         'find_one_and_delete', 'google_nonce'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.auth)

    def test_google_credential_checks(self):
        for fragment in ('verify_oauth2_token', 'email_verified', 'claims.get("nonce")',
                         'claims.get("sub")', 'claims.get("iss")'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.identity)

    def test_frontend_google_endpoint_contract(self):
        for fragment in ('/auth/google/config', '/auth/google/link', '/auth/google',
                         'setToken(result.token)', 'refreshRef.current()'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.button)
        self.assertIn('<GoogleSignIn />', self.login)
        self.assertIn('<GoogleSignIn registration={f}', self.register)

    def test_role_routes_exist(self):
        for fragment in ('"/admin"', '"/parceiro"', '"/influencer"'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.app)
                self.assertIn(fragment, self.button)


if __name__ == "__main__":
    unittest.main()
