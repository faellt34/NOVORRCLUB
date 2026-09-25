"""Iter 20 — Abandon analysis (funnel + WS realtime) tests"""
import os, uuid, time, json, asyncio, threading
import requests, pytest

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

ADMIN = ("faellt@gmail.com", "Robson2026!")
PARTNER = ("parceiro.exemplo@club.pt", "parceiro123")

BROWSER_UA_TEMPLATE = "Mozilla/5.0 (Iter20 Test {tag}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def partner_token():
    return _login(*PARTNER)


def _click(src="instagram", tag=None):
    tag = tag or uuid.uuid4().hex[:8]
    ua = BROWSER_UA_TEMPLATE.format(tag=tag)
    r = requests.get(f"{API}/public/coupon/CLUB-10", params={"src": src}, headers={"User-Agent": ua}, timeout=15)
    return r, ua, tag


def test_public_coupon_returns_claim_id():
    r, ua, tag = _click("instagram")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "claim_id" in data and data["claim_id"]
    assert data["cupom"] == "CLUB-10"


def test_qr_downloaded_ok_and_bad_claim_404():
    r, ua, tag = _click("instagram")
    claim_id = r.json()["claim_id"]

    ok = requests.post(f"{API}/public/coupon/CLUB-10/qr-downloaded", json={"claim_id": claim_id}, timeout=15)
    assert ok.status_code == 200 and ok.json().get("ok") is True

    bad = requests.post(f"{API}/public/coupon/CLUB-10/qr-downloaded", json={"claim_id": "cl_doesnotexist_xxx"}, timeout=15)
    assert bad.status_code == 404


def test_analysis_requires_admin(partner_token):
    h = {"Authorization": f"Bearer {partner_token}"}
    r = requests.get(f"{API}/admin/cliques/analysis", params={"period": "hoje"}, headers=h, timeout=15)
    assert r.status_code == 403


def _get_analysis(admin_token, period="7d"):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{API}/admin/cliques/analysis", params={"period": period}, headers=h, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def test_analysis_periods_and_counts_consistency(admin_token):
    for p in ("hoje", "7d", "30d"):
        d = _get_analysis(admin_token, p)
        for k in ("total", "sem_download", "qr_sem_scan", "convertidos", "lista"):
            assert k in d, f"missing key {k} in {p}"
        assert d["total"] == d["sem_download"] + d["qr_sem_scan"] + d["convertidos"], f"counts mismatch for {p}: {d['total']} vs {d['sem_download']}+{d['qr_sem_scan']}+{d['convertidos']}"
        assert d["total"] == len(d["lista"])


def test_full_funnel_qr_sem_scan_then_converteu(admin_token, partner_token):
    # 1) New click
    r, ua, tag = _click("instagram")
    assert r.status_code == 200
    claim_id = r.json()["claim_id"]
    time.sleep(0.5)

    d1 = _get_analysis(admin_token, "hoje")
    row1 = next((x for x in d1["lista"] if x["id"] == claim_id), None)
    assert row1 is not None, f"claim {claim_id} not found in analysis hoje"
    assert row1["qr"] is False
    assert row1["estado"] in ("Sem download", "Abandonou")

    # 2) QR downloaded
    ok = requests.post(f"{API}/public/coupon/CLUB-10/qr-downloaded", json={"claim_id": claim_id}, timeout=15)
    assert ok.status_code == 200
    time.sleep(0.5)

    d2 = _get_analysis(admin_token, "hoje")
    row2 = next((x for x in d2["lista"] if x["id"] == claim_id), None)
    assert row2 is not None
    assert row2["qr"] is True
    assert row2["estado"] == "QR sem scan", f"expected QR sem scan, got {row2['estado']}"

    # 3) Redemption (partner) marks converted
    idem = f"iter20-{uuid.uuid4().hex[:10]}"
    rr = requests.post(f"{API}/redemptions", json={"code": "CLUB-10", "amount": 45, "idempotency_key": idem},
                       headers={"Authorization": f"Bearer {partner_token}"}, timeout=15)
    assert rr.status_code == 200, rr.text
    time.sleep(0.7)

    d3 = _get_analysis(admin_token, "hoje")
    row3 = next((x for x in d3["lista"] if x["id"] == claim_id), None)
    assert row3 is not None
    assert row3["estado"] == "Converteu", f"expected Converteu, got {row3['estado']}"
    assert float(row3["valor"]) == 45.0
    # counts still consistent
    assert d3["total"] == d3["sem_download"] + d3["qr_sem_scan"] + d3["convertidos"]
    # Save ids so main agent can wipe
    print(f"\nSEED_CREATED claim_id={claim_id} redemption_idem={idem} amount=45")


# ---------- WS realtime ----------

def test_ws_events_novo_clique_qr_baixado_venda(admin_token, partner_token):
    try:
        from websockets.sync.client import connect as ws_connect
    except Exception:
        pytest.skip("websockets sync client not available")

    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + f"/api/ws/dashboard?token={admin_token}"
    events = []

    def reader(ws, stop_at):
        try:
            while time.time() < stop_at:
                try:
                    msg = ws.recv(timeout=1.0)
                    events.append(json.loads(msg))
                except TimeoutError:
                    continue
                except Exception:
                    break
        except Exception:
            pass

    with ws_connect(ws_url, open_timeout=10) as ws:
        stop_at = time.time() + 12
        t = threading.Thread(target=reader, args=(ws, stop_at), daemon=True)
        t.start()
        time.sleep(0.5)

        # Trigger a click
        r, ua, tag = _click("instagram")
        assert r.status_code == 200
        claim_id = r.json()["claim_id"]
        time.sleep(1.0)

        # Trigger qr downloaded
        requests.post(f"{API}/public/coupon/CLUB-10/qr-downloaded", json={"claim_id": claim_id}, timeout=15)
        time.sleep(1.0)

        # Trigger redemption
        idem = f"iter20ws-{uuid.uuid4().hex[:10]}"
        rr = requests.post(f"{API}/redemptions", json={"code": "CLUB-10", "amount": 30, "idempotency_key": idem},
                           headers={"Authorization": f"Bearer {partner_token}"}, timeout=15)
        assert rr.status_code == 200
        time.sleep(2.0)

        t.join(timeout=3)
        print(f"\nWS_SEED claim_id={claim_id} redemption_idem={idem} amount=30")

    types = [e.get("tipo") for e in events]
    print(f"WS events received ({len(events)}): {types}")

    # novo_clique
    nc = [e for e in events if e.get("tipo") == "novo_clique" and (e.get("dados", {}).get("id") == claim_id)]
    assert nc, f"no novo_clique event with claim_id={claim_id}. Got events={events}"

    # qr_baixado
    qb = [e for e in events if e.get("tipo") == "qr_baixado" and e.get("claim_id") == claim_id]
    assert qb, f"no qr_baixado event with claim_id={claim_id}. Got types={types}"

    # venda
    vd = [e for e in events if e.get("tipo") == "venda" and e.get("claim_id") == claim_id]
    assert vd, f"no venda event with claim_id={claim_id}. Got types={types}"
    assert float(vd[0].get("valor", 0)) == 30.0
