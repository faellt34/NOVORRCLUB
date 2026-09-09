"""
Robson Club — Iteration 5 tests:
  - Statement PDF (influencer)
  - Feedback create + admin status
  - Subscription cancel (no active sub → 404) + GET /payments/subscription
  - Forgot-password with RESEND vazio (message + admin reset list flag emailed=false)
  - Regression: login all roles, /dashboard/partner, /admin/campanhas, /ebooks
"""
import os
import uuid
from pathlib import Path

import pytest
import requests

for line in Path("/app/frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        os.environ.setdefault("BASE_URL", line.split("=", 1)[1].strip())
BASE = os.environ["BASE_URL"].rstrip("/") + "/api"

ADMIN = ("admin@robson.club", "admin123")
INFLU = ("robson@robson.club", "robson123")
MARTA = ("marta@robson.club", "marta123")
PARTNER = ("gerencia@tivolisky.pt", "tivoli123")


def _login(email, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    assert r.status_code == 200, f"login {email} → {r.status_code} {r.text}"
    return r.json()["token"]


def H(t): return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def admin_tok(): return _login(*ADMIN)


@pytest.fixture(scope="module")
def influ_tok(): return _login(*INFLU)


@pytest.fixture(scope="module")
def marta_tok(): return _login(*MARTA)


@pytest.fixture(scope="module")
def partner_tok(): return _login(*PARTNER)


class TestStatementPdf:
    def test_influencer_month_pdf(self, influ_tok):
        stmts = requests.get(f"{BASE}/statements", headers=H(influ_tok)).json()
        assert isinstance(stmts, list) and stmts, "influencer has no statements"
        month = stmts[0]["id"]
        r = requests.get(f"{BASE}/statements/{month}/pdf", headers=H(influ_tok))
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert len(r.content) > 1000
        assert r.content[:5] == b"%PDF-"

    def test_empty_month_404(self, influ_tok):
        r = requests.get(f"{BASE}/statements/2020-01/pdf", headers=H(influ_tok))
        assert r.status_code == 404

    def test_partner_forbidden(self, partner_tok):
        r = requests.get(f"{BASE}/statements/2025-01/pdf", headers=H(partner_tok))
        assert r.status_code == 403


class TestFeedback:
    def test_create_feedback_and_admin_flow(self, influ_tok, admin_tok):
        msg = f"Teste de sugestão automática {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/feedback",
                          json={"tipo": "Melhoria", "mensagem": msg, "pagina": "/x"},
                          headers=H(influ_tok))
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["status"] == "Novo"
        assert doc["tipo"] == "Melhoria"
        assert doc["mensagem"] == msg
        fb_id = doc["id"]

        # short message → 400
        r = requests.post(f"{BASE}/feedback",
                          json={"tipo": "Melhoria", "mensagem": "abc", "pagina": "/x"},
                          headers=H(influ_tok))
        assert r.status_code == 400

        # admin lists
        r = requests.get(f"{BASE}/admin/feedback", headers=H(admin_tok))
        assert r.status_code == 200
        items = r.json()
        found = [x for x in items if x["id"] == fb_id]
        assert found, "feedback not present in admin list"

        # change status
        r = requests.post(f"{BASE}/admin/feedback/{fb_id}/status",
                          json={"status": "Em análise"}, headers=H(admin_tok))
        assert r.status_code == 200 and r.json()["ok"] is True

        # reflected
        items = requests.get(f"{BASE}/admin/feedback", headers=H(admin_tok)).json()
        assert next(x for x in items if x["id"] == fb_id)["status"] == "Em análise"

        # invalid status
        r = requests.post(f"{BASE}/admin/feedback/{fb_id}/status",
                          json={"status": "Xpto"}, headers=H(admin_tok))
        assert r.status_code == 400

        # influencer forbidden from admin listing
        r = requests.get(f"{BASE}/admin/feedback", headers=H(influ_tok))
        assert r.status_code == 403

        # admin got notification of tipo feedback
        n = requests.get(f"{BASE}/notifications", headers=H(admin_tok)).json()
        items = n.get("items", []) if isinstance(n, dict) else n
        assert any(x.get("tipo") == "feedback" for x in items)


class TestSubscriptionCancel:
    def test_cancel_no_active_404(self, influ_tok):
        r = requests.post(f"{BASE}/payments/subscription/cancel", headers=H(influ_tok))
        assert r.status_code == 404

    def test_get_subscription_null_or_200(self, influ_tok):
        r = requests.get(f"{BASE}/payments/subscription", headers=H(influ_tok))
        assert r.status_code == 200
        # None or dict
        j = r.json()
        assert j is None or isinstance(j, dict)


class TestForgotResendEmpty:
    def test_forgot_marta_message_and_admin_flag(self, admin_tok):
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": "marta@robson.club"})
        assert r.status_code == 200
        j = r.json()
        assert j["ok"] is True
        # RESEND vazio → message must mention administrador
        assert "administrador" in j.get("message", "").lower()

        reqs = requests.get(f"{BASE}/admin/reset-requests", headers=H(admin_tok)).json()
        marta = [x for x in reqs if x["email"] == "marta@robson.club"]
        assert marta, "marta reset request not visible to admin"
        # emailed should be false since RESEND is empty
        assert marta[0].get("emailed") is False


class TestRegression:
    def test_login_admin(self): assert _login(*ADMIN)
    def test_login_influencer(self): assert _login(*INFLU)
    def test_login_partner(self): assert _login(*PARTNER)

    def test_partner_dashboard(self, partner_tok):
        r = requests.get(f"{BASE}/dashboard/partner", headers=H(partner_tok))
        assert r.status_code == 200

    def test_admin_campanhas(self, admin_tok):
        r = requests.get(f"{BASE}/admin/campanhas", headers=H(admin_tok))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ebooks(self, influ_tok):
        r = requests.get(f"{BASE}/ebooks", headers=H(influ_tok))
        assert r.status_code == 200
        assert isinstance(r.json(), list)
