"""
Robson Club — backend end-to-end API tests.
Covers: auth, RBAC, dashboards, redemptions (idempotency), leads approve/reject,
admin CRUD, messages, statements, ebooks, notifications, audit.
"""
import os
import uuid
import time
import pytest
import requests
from pathlib import Path

# Load frontend .env to reach the public URL used by the UI.
FRONTEND_ENV = Path("/app/frontend/.env")
for line in FRONTEND_ENV.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        os.environ.setdefault("BASE_URL", line.split("=", 1)[1].strip())

BASE = os.environ["BASE_URL"].rstrip("/") + "/api"

ADMIN = ("admin@robson.club", "admin123")
INFLU = ("robson@robson.club", "robson123")
PARTN = ("gerencia@tivolisky.pt", "tivoli123")
BELCA = ("reservas@belcanto.pt", "belcanto123")


def _login(email, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="session")
def admin():
    t, u = _login(*ADMIN); return t, u


@pytest.fixture(scope="session")
def influ():
    t, u = _login(*INFLU); return t, u


@pytest.fixture(scope="session")
def partner():
    t, u = _login(*PARTN); return t, u


# ---------- AUTH ----------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{BASE}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
        assert r.status_code == 200
        j = r.json(); assert "token" in j and j["user"]["role"] == "admin"
        assert "password_hash" not in j["user"]

    def test_login_invalid(self):
        r = requests.post(f"{BASE}/auth/login", json={"email": ADMIN[0], "password": "wrong-xyz"})
        assert r.status_code == 401

    def test_me_with_token(self, admin):
        t, _ = admin
        r = requests.get(f"{BASE}/auth/me", headers=_h(t))
        assert r.status_code == 200 and r.json()["role"] == "admin"

    def test_me_without_token(self):
        r = requests.get(f"{BASE}/auth/me")
        assert r.status_code == 401


# ---------- RBAC ----------
class TestRBAC:
    def test_influencer_forbidden_partner_dashboard(self, influ):
        t, _ = influ
        assert requests.get(f"{BASE}/dashboard/partner", headers=_h(t)).status_code == 403

    def test_influencer_forbidden_admin(self, influ):
        t, _ = influ
        assert requests.get(f"{BASE}/admin/usuarios", headers=_h(t)).status_code == 403

    def test_partner_forbidden_influencer_dashboard(self, partner):
        t, _ = partner
        assert requests.get(f"{BASE}/dashboard/influencer", headers=_h(t)).status_code == 403


# ---------- Dashboards ----------
class TestDashboards:
    @pytest.mark.parametrize("p", [7, 30, 90])
    def test_influencer_dashboard(self, influ, p):
        t, _ = influ
        r = requests.get(f"{BASE}/dashboard/influencer?period={p}", headers=_h(t))
        assert r.status_code == 200
        j = r.json()
        for k in ("kpis", "chart", "campaigns", "topPartners"):
            assert k in j
        assert "featured" in j

    def test_partner_dashboard(self, partner):
        t, _ = partner
        r = requests.get(f"{BASE}/dashboard/partner", headers=_h(t))
        assert r.status_code == 200
        j = r.json()
        for k in ("totals", "leaderboard", "redemptions"):
            assert k in j

    def test_admin_dashboard(self, admin):
        t, _ = admin
        r = requests.get(f"{BASE}/dashboard/admin", headers=_h(t))
        assert r.status_code == 200
        assert "totals" in r.json() and "counts" in r.json()

    def test_audit_admin_only(self, admin, influ):
        t, _ = admin
        r = requests.get(f"{BASE}/audit", headers=_h(t))
        assert r.status_code == 200 and isinstance(r.json(), list)
        t2, _ = influ
        assert requests.get(f"{BASE}/audit", headers=_h(t2)).status_code == 403


# ---------- Redemptions ----------
class TestRedemptions:
    def test_redemption_flow(self, partner, admin, influ):
        t, _ = partner
        key = str(uuid.uuid4())
        # Use amount unique enough to avoid the 10s duplicate guard from other tests
        amount = 150.0 + (time.time() % 1)
        amount = round(amount, 2)
        r = requests.post(f"{BASE}/redemptions", headers=_h(t),
                          json={"code": "ROBSON-LUXE-25", "amount": amount, "idempotency_key": key})
        assert r.status_code == 200, r.text
        rec = r.json()["record"]
        assert r.json()["duplicate"] is False
        assert rec["rate"] == 0.1
        assert rec["commission"] == round(amount * 0.1, 2)
        rec_id = rec["id"]

        # Same idempotency key -> duplicate:true, same id
        r2 = requests.post(f"{BASE}/redemptions", headers=_h(t),
                           json={"code": "ROBSON-LUXE-25", "amount": amount, "idempotency_key": key})
        assert r2.status_code == 200
        assert r2.json()["duplicate"] is True
        assert r2.json()["record"]["id"] == rec_id

        # New key, same code+amount within 10s -> 409
        r3 = requests.post(f"{BASE}/redemptions", headers=_h(t),
                           json={"code": "ROBSON-LUXE-25", "amount": amount,
                                 "idempotency_key": str(uuid.uuid4())})
        assert r3.status_code == 409

        # Audit log includes REDENÇÃO
        ta, _ = admin
        audit = requests.get(f"{BASE}/audit?limit=20", headers=_h(ta)).json()
        assert any(a["action"] == "REDENÇÃO" and rec_id == a.get("ref") for a in audit)

        # Notifications for influencer
        ti, _ = influ
        notes = requests.get(f"{BASE}/notifications", headers=_h(ti)).json()
        assert any(n["tipo"] == "redencao" for n in notes["items"])

    def test_expired_coupon_returns_404_at_tivoli(self, partner):
        t, _ = partner
        r = requests.post(f"{BASE}/redemptions", headers=_h(t),
                          json={"code": "ROBSON-DOURO-10", "amount": 50,
                                "idempotency_key": str(uuid.uuid4())})
        # Douro belongs to p5, not Tivoli -> 404 (not found for this partner)
        assert r.status_code == 404

    def test_other_partner_coupon_404(self, partner):
        t, _ = partner
        r = requests.post(f"{BASE}/redemptions", headers=_h(t),
                          json={"code": "ROBSON-BEL-10", "amount": 80,
                                "idempotency_key": str(uuid.uuid4())})
        assert r.status_code == 404

    def test_zero_amount(self, partner):
        t, _ = partner
        r = requests.post(f"{BASE}/redemptions", headers=_h(t),
                          json={"code": "ROBSON-LUXE-25", "amount": 0,
                                "idempotency_key": str(uuid.uuid4())})
        assert r.status_code == 400


# ---------- Leads ----------
class TestLeads:
    def test_lead_create_approve_and_login(self, influ, admin):
        ti, _ = influ
        email = f"partner-{uuid.uuid4().hex[:8]}@novo.pt"
        payload = {"nome": f"Espaço {uuid.uuid4().hex[:6]}", "categoria": "Restaurante",
                   "cidade": "Lisboa", "contacto": email, "nota": "teste"}
        r = requests.post(f"{BASE}/leads", headers=_h(ti), json=payload)
        assert r.status_code == 200
        lead = r.json()
        assert lead["status"] == "Novo"
        lead_id = lead["id"]

        ta, _ = admin
        leads = requests.get(f"{BASE}/leads", headers=_h(ta)).json()
        assert any(l["id"] == lead_id for l in leads)

        # Approve
        r = requests.post(f"{BASE}/leads/{lead_id}/approve", headers=_h(ta), json={"note": "ok"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["lead"]["status"] == "Aprovada"
        assert j["access_email"] == email

        # Partner appears in list
        partners = requests.get(f"{BASE}/admin/parceiros", headers=_h(ta)).json()
        assert any(p["nome"] == payload["nome"] for p in partners)

        # Login with new partner
        tok, u = _login(email, "parceiro123")
        assert u["role"] == "partner"

        # Duplicate approve -> 409
        r = requests.post(f"{BASE}/leads/{lead_id}/approve", headers=_h(ta), json={"note": ""})
        assert r.status_code == 409

        # Influencer got approval notification
        notes = requests.get(f"{BASE}/notifications", headers=_h(ti)).json()
        assert any(n["tipo"] == "lead_aprovada" for n in notes["items"])

    def test_lead_reject(self, influ, admin):
        ti, _ = influ
        r = requests.post(f"{BASE}/leads", headers=_h(ti),
                          json={"nome": f"Rej {uuid.uuid4().hex[:6]}", "categoria": "Hotel",
                                "cidade": "Porto", "contacto": "sem-email", "nota": ""})
        lead_id = r.json()["id"]
        ta, _ = admin
        r = requests.post(f"{BASE}/leads/{lead_id}/reject", headers=_h(ta), json={"note": "fora do target"})
        assert r.status_code == 200
        assert r.json()["status"] == "Rejeitada"
        notes = requests.get(f"{BASE}/notifications", headers=_h(ti)).json()
        assert any(n["tipo"] == "lead_rejeitada" for n in notes["items"])


# ---------- Admin CRUD ----------
class TestAdminCrud:
    def test_campaign_crud_and_validations(self, admin):
        t, _ = admin
        cupom = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{BASE}/admin/campanhas", headers=_h(t),
                          json={"nome": "Teste", "parceiro": "Belcanto", "influencer": "@marta.lx",
                                "cupom": cupom, "desconto": 10, "comissao": 15, "validade": "2027-01-01", "status": "Ativa"})
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["parceiro_id"] == "p2"
        cid = c["id"]

        # Duplicate cupom -> 409
        r = requests.post(f"{BASE}/admin/campanhas", headers=_h(t),
                          json={"nome": "Dup", "parceiro": "Belcanto", "influencer": "@marta.lx",
                                "cupom": cupom, "desconto": 10, "comissao": 15, "validade": "2027-01-01"})
        assert r.status_code == 409

        # Invalid parceiro -> 400
        r = requests.post(f"{BASE}/admin/campanhas", headers=_h(t),
                          json={"nome": "Bad", "parceiro": "DoesNotExist", "influencer": "@marta.lx",
                                "cupom": f"XX-{uuid.uuid4().hex[:4]}", "desconto": 5, "comissao": 5, "validade": "2027-01-01"})
        assert r.status_code == 400

        # Delete
        r = requests.delete(f"{BASE}/admin/campanhas/{cid}", headers=_h(t))
        assert r.status_code == 200

    def test_user_crud_no_password_hash(self, admin):
        t, u = admin
        email = f"newuser-{uuid.uuid4().hex[:6]}@robson.club"
        r = requests.post(f"{BASE}/admin/usuarios", headers=_h(t),
                          json={"nome": "Novo", "email": email, "papel": "Influencer"})
        assert r.status_code == 200
        new = r.json()
        assert "password_hash" not in new
        assert new["papel"] == "Influencer"
        # Login with default password
        tok, uu = _login(email, "robson123")
        assert uu["email"] == email

        # List never exposes password_hash
        lst = requests.get(f"{BASE}/admin/usuarios", headers=_h(t)).json()
        assert all("password_hash" not in x for x in lst)

        # Cannot delete self
        r = requests.delete(f"{BASE}/admin/usuarios/{u['id']}", headers=_h(t))
        assert r.status_code == 400

        # Cleanup
        requests.delete(f"{BASE}/admin/usuarios/{new['id']}", headers=_h(t))


# ---------- Messages ----------
class TestMessages:
    def test_contacts_and_conversation(self, admin, influ):
        ta, ua = admin
        ti, ui = influ
        # Admin contacts include everyone
        cs = requests.get(f"{BASE}/messages/contacts", headers=_h(ta)).json()
        ids = {c["id"] for c in cs}
        assert ui["id"] in ids
        # Influencer contacts include admins + partners of their campaigns (tivoli/belcanto)
        cs2 = requests.get(f"{BASE}/messages/contacts", headers=_h(ti)).json()
        ids2 = {c["id"] for c in cs2}
        assert ua["id"] in ids2

        # Admin creates a conversation with influencer + msg
        r = requests.post(f"{BASE}/messages/conversations", headers=_h(ta),
                          json={"participant_id": ui["id"], "text": "Olá do admin"})
        assert r.status_code == 200
        conv_id = r.json()["id"]

        # Influencer unread-count > 0
        uc = requests.get(f"{BASE}/messages/unread-count", headers=_h(ti)).json()
        assert uc["unread"] >= 1

        # Read messages
        r = requests.get(f"{BASE}/messages/conversations/{conv_id}", headers=_h(ti))
        assert r.status_code == 200
        # After GET, unread should decrease
        uc2 = requests.get(f"{BASE}/messages/unread-count", headers=_h(ti)).json()
        assert uc2["unread"] <= uc["unread"]

    def test_influencer_cannot_message_unrelated(self, influ, admin):
        ti, _ = influ
        # Find an influencer that is NOT in influencer's contact list
        ta, _ = admin
        all_users = requests.get(f"{BASE}/admin/usuarios", headers=_h(ta)).json()
        contacts = requests.get(f"{BASE}/messages/contacts", headers=_h(ti)).json()
        contact_ids = {c["id"] for c in contacts}
        me_id = requests.get(f"{BASE}/auth/me", headers=_h(ti)).json()["id"]
        other = next((u for u in all_users if u["role"] == "influencer" and u["id"] not in contact_ids and u["id"] != me_id), None)
        if not other:
            pytest.skip("no unrelated user available")
        r = requests.post(f"{BASE}/messages/conversations", headers=_h(ti),
                          json={"participant_id": other["id"], "text": "hi"})
        assert r.status_code == 403


# ---------- Statements & Ebooks ----------
class TestData:
    def test_statements(self, influ):
        t, _ = influ
        r = requests.get(f"{BASE}/statements", headers=_h(t))
        assert r.status_code == 200
        s = r.json()
        assert isinstance(s, list) and len(s) >= 1
        assert all(m["status"] in ("Pago", "Pendente") for m in s)
        assert all("lines" in m for m in s)

    def test_ebooks(self, influ):
        t, _ = influ
        r = requests.get(f"{BASE}/ebooks", headers=_h(t))
        assert r.status_code == 200
        eb = r.json()
        assert len(eb) == 12
        countries = {e["pais"] for e in eb}
        assert {"Portugal", "Espanha", "Itália", "França", "Emirados"}.issubset(countries)
