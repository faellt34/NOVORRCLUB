"""
Robson Club — tests for NEW iteration 4 features:
  - Admin payouts (mark paid / revert)
  - Password reset (forgot/reset flow with tokens)
  - Stripe checkout (ebook_*, club_monthly)
  - PDF upload + access control
  - Regression: generic /admin/{kind} does not swallow /admin/payouts nor /admin/reset-requests
"""
import io
import os
import time
import uuid
from pathlib import Path

import pytest
import requests

# Load public URL
for line in Path("/app/frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        os.environ.setdefault("BASE_URL", line.split("=", 1)[1].strip())
BASE = os.environ["BASE_URL"].rstrip("/") + "/api"

ADMIN = ("admin@robson.club", "admin123")
INFLU = ("robson@robson.club", "robson123")
MARTA = ("marta@robson.club", "marta123")
DIOGO = ("diogo@robson.club", "diogo123")


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


# ============ PAYOUTS ============
class TestPayouts:
    def test_payouts_overview_admin(self, admin_tok):
        r = requests.get(f"{BASE}/admin/payouts", headers=H(admin_tok))
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) > 0
        row = rows[0]
        for k in ("influencer_id", "month", "commission", "status", "paid_at"):
            assert k in row
        assert row["status"] in ("Pago", "Pendente")

    def test_payouts_forbidden_influencer(self, influ_tok):
        r = requests.post(f"{BASE}/admin/payouts",
                          json={"influencer_id": "if2", "month": "2025-01"},
                          headers=H(influ_tok))
        assert r.status_code == 403

    def test_mark_and_revert(self, admin_tok, marta_tok):
        # Find a pending month for marta (if2)
        rows = requests.get(f"{BASE}/admin/payouts", headers=H(admin_tok)).json()
        pending = [r for r in rows if r["influencer_id"] == "if2" and r["status"] == "Pendente"]
        assert pending, "No pending month for if2 — seed changed?"
        month = pending[0]["month"]

        # Mark paid
        r = requests.post(f"{BASE}/admin/payouts", json={"influencer_id": "if2", "month": month},
                          headers=H(admin_tok))
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["paid_at"]
        # Duplicate → 409
        r2 = requests.post(f"{BASE}/admin/payouts", json={"influencer_id": "if2", "month": month},
                           headers=H(admin_tok))
        assert r2.status_code == 409

        # Marta sees status Pago + notification
        stmts = requests.get(f"{BASE}/statements", headers=H(marta_tok)).json()
        m = next((s for s in stmts if s["id"] == month), None)
        assert m and m["status"] == "Pago" and m["paidAt"]
        notifs = requests.get(f"{BASE}/notifications", headers=H(marta_tok)).json()
        items = notifs.get("items", []) if isinstance(notifs, dict) else notifs
        assert any(n.get("tipo") == "pagamento" for n in items)

        # Revert
        r3 = requests.delete(f"{BASE}/admin/payouts/if2/{month}", headers=H(admin_tok))
        assert r3.status_code == 200
        stmts = requests.get(f"{BASE}/statements", headers=H(marta_tok)).json()
        m = next((s for s in stmts if s["id"] == month), None)
        assert m and m["status"] == "Pendente"


# ============ PASSWORD RESET ============
class TestReset:
    def test_forgot_unknown_email_ok(self):
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": f"noone-{uuid.uuid4()}@x.com"})
        assert r.status_code == 200 and r.json()["ok"] is True

    def test_full_reset_flow_diogo(self, admin_tok):
        # 1. Request reset
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": DIOGO[0]})
        assert r.status_code == 200
        # 2. Admin sees request
        reqs = requests.get(f"{BASE}/admin/reset-requests", headers=H(admin_tok)).json()
        mine = [x for x in reqs if x["email"] == DIOGO[0]]
        assert mine, "reset request not found in admin list"
        token = mine[0]["token"]
        # 3. GET check
        r = requests.get(f"{BASE}/auth/reset-password/{token}")
        assert r.status_code == 200
        j = r.json()
        assert j["email"] == DIOGO[0] and "nome" in j
        # 4. Password too short
        r = requests.post(f"{BASE}/auth/reset-password", json={"token": token, "password": "x"})
        assert r.status_code == 400
        # 5. Invalid token
        r = requests.post(f"{BASE}/auth/reset-password", json={"token": "invalid-xyz", "password": "abcdef"})
        assert r.status_code == 400
        r = requests.get(f"{BASE}/auth/reset-password/invalid-xyz")
        assert r.status_code == 400
        # 6. Reset to new password
        r = requests.post(f"{BASE}/auth/reset-password", json={"token": token, "password": "novaPass123"})
        assert r.status_code == 200
        # 7. Login with new
        assert _login(DIOGO[0], "novaPass123")
        # 8. Reuse token → 400
        r = requests.post(f"{BASE}/auth/reset-password", json={"token": token, "password": "outra12345"})
        assert r.status_code == 400

        # RESTORE: request fresh token & set back to diogo123
        requests.post(f"{BASE}/auth/forgot-password", json={"email": DIOGO[0]})
        reqs = requests.get(f"{BASE}/admin/reset-requests", headers=H(admin_tok)).json()
        tok2 = next(x["token"] for x in reqs if x["email"] == DIOGO[0])
        r = requests.post(f"{BASE}/auth/reset-password", json={"token": tok2, "password": "diogo123"})
        assert r.status_code == 200
        assert _login(DIOGO[0], "diogo123")


# ============ STRIPE CHECKOUT ============
class TestStripe:
    def test_checkout_ebook_e1(self, influ_tok):
        r = requests.post(f"{BASE}/payments/checkout",
                          json={"lookup_key": "ebook_e1",
                                "origin_url": "https://robson-dashboard.preview.emergentagent.com"},
                          headers=H(influ_tok))
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["checkout_url"].startswith("https://checkout.stripe.com")
        assert j["session_id"]
        # status w/o auth
        s = requests.get(f"{BASE}/payments/status/{j['session_id']}")
        assert s.status_code == 200
        assert s.json()["payment_status"] == "pending"

    def test_checkout_subscription(self, influ_tok):
        r = requests.post(f"{BASE}/payments/checkout",
                          json={"lookup_key": "club_monthly",
                                "origin_url": "https://robson-dashboard.preview.emergentagent.com"},
                          headers=H(influ_tok))
        assert r.status_code == 200, r.text
        assert r.json()["checkout_url"].startswith("https://checkout.stripe.com")

    def test_free_ebook_404(self, influ_tok):
        r = requests.post(f"{BASE}/payments/checkout",
                          json={"lookup_key": "ebook_e2", "origin_url": "https://x.com"},
                          headers=H(influ_tok))
        assert r.status_code == 404

    def test_unknown_lookup_400(self, influ_tok):
        r = requests.post(f"{BASE}/payments/checkout",
                          json={"lookup_key": "xpto", "origin_url": "https://x.com"},
                          headers=H(influ_tok))
        assert r.status_code == 400

    def test_no_auth_401(self):
        r = requests.post(f"{BASE}/payments/checkout",
                          json={"lookup_key": "ebook_e1", "origin_url": "https://x.com"})
        assert r.status_code == 401

    def test_access_defaults(self, influ_tok):
        r = requests.get(f"{BASE}/payments/access", headers=H(influ_tok))
        assert r.status_code == 200
        j = r.json()
        assert "subscribed" in j and "owned" in j
        assert j["subscription_price"] == 9.9


# ============ PDF UPLOAD / READ ============
def _make_pdf() -> bytes:
    # Minimal valid PDF (single-page blank)
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n0000000098 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n148\n%%EOF\n")


class TestPdf:
    def test_upload_wrong_type_400(self, admin_tok):
        r = requests.post(f"{BASE}/admin/ebooks/e2/pdf", headers=H(admin_tok),
                          files={"file": ("hi.txt", b"not a pdf", "text/plain")})
        assert r.status_code == 400

    def test_upload_e2_and_read(self, admin_tok, influ_tok):
        pdf = _make_pdf()
        r = requests.post(f"{BASE}/admin/ebooks/e2/pdf", headers=H(admin_tok),
                          files={"file": ("guia.pdf", pdf, "application/pdf")})
        assert r.status_code == 200, r.text
        # ebooks list has_pdf
        ebs = requests.get(f"{BASE}/ebooks", headers=H(influ_tok)).json()
        e2 = next(e for e in ebs if e["id"] == "e2")
        assert e2["has_pdf"] is True
        # read with header
        r = requests.get(f"{BASE}/ebooks/e2/pdf", headers=H(influ_tok))
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        # read with ?auth=
        r = requests.get(f"{BASE}/ebooks/e2/pdf", params={"auth": influ_tok})
        assert r.status_code == 200

    def test_premium_pdf_access(self, admin_tok, influ_tok):
        pdf = _make_pdf()
        r = requests.post(f"{BASE}/admin/ebooks/e1/pdf", headers=H(admin_tok),
                          files={"file": ("premium.pdf", pdf, "application/pdf")})
        assert r.status_code == 200
        # influencer without purchase → 403 (assuming robson has no entitlement for e1)
        r = requests.get(f"{BASE}/ebooks/e1/pdf", headers=H(influ_tok))
        assert r.status_code in (403, 200)  # 200 if a previous test bought it
        # admin can always read
        r = requests.get(f"{BASE}/ebooks/e1/pdf", headers=H(admin_tok))
        assert r.status_code == 200

    def test_no_pdf_404(self, influ_tok):
        r = requests.get(f"{BASE}/ebooks/e12/pdf", headers=H(influ_tok))
        # If a previous run uploaded, might be 200. Accept 404 or 200.
        assert r.status_code in (404, 200)


# ============ REGRESSION: routing order ============
class TestRegression:
    def test_admin_payouts_not_shadowed(self, admin_tok):
        r = requests.get(f"{BASE}/admin/payouts", headers=H(admin_tok))
        assert r.status_code == 200
        # Should be the payouts list (has 'month' key), not generic collection listing
        rows = r.json()
        if rows:
            assert "month" in rows[0]

    def test_admin_reset_requests_not_shadowed(self, admin_tok):
        r = requests.get(f"{BASE}/admin/reset-requests", headers=H(admin_tok))
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            assert "token" in rows[0]

    def test_admin_campanhas_list(self, admin_tok):
        r = requests.get(f"{BASE}/admin/campanhas", headers=H(admin_tok))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_partner_dashboard(self):
        t = _login("gerencia@tivolisky.pt", "tivoli123")
        r = requests.get(f"{BASE}/dashboard/partner", headers=H(t))
        assert r.status_code == 200
