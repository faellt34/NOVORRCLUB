"""Maria Eduarda BR/PT: independent TEST ONLY identities and financial lifecycles.

No production Mongo, no actual customers, no Connect creation, no transfer
or Stripe API calls. Provider records are mocks with explicit fake IDs.
"""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from tests.test_pix_service import env, body, paid, run
from tests.test_payment_http_integration import pt, request, signed_event, ORIGIN
import routes_pix as pix


def profiles():
    data = json.loads((Path(__file__).parent / "fixtures" / "maria_eduarda_sandbox.json").read_text())
    assert data["rules"]["production_modified"] is False
    return {p["country"]: p for p in data["profiles"]}


def test_accounts_created_as_distinct_offline_fixtures_only():
    both = profiles()
    assert set(both) == {"BR", "PT"}
    assert {both["BR"]["currency"], both["PT"]["currency"]} == {"brl", "eur"}
    assert {both["BR"]["name"], both["PT"]["name"]} == {"Maria Eduarda"}
    assert both["BR"]["id"] != both["PT"]["id"]
    assert both["BR"]["email"] != both["PT"]["email"]
    for p in both.values():
        assert p["is_test"] is True
        assert p["role"] == "influencer"
        assert p["email"].endswith("@rrclub.invalid")
        assert p["stripe_connect_account_id"] is None
        assert p["mock_stripe_account_id"].startswith("mock_")
        assert p["connect_verification"] == "simulated_only"


def use_maria_br(env):
    p = profiles()["BR"]
    db = env[0]
    db.campaigns.items[0]["influencer_id"] = p["id"]
    db.influencers.items[0].update({
        "id": p["id"], "nome": p["name"], "status": "Ativo",
        "is_test": True, "pix_stripe_account_id": p["mock_stripe_account_id"],
    })
    client = pix.stripe_client().v1
    base = client.accounts.retrieve.return_value
    def mocked_connected_account(account_id, **kwargs):
        return {**base, "metadata": {
            "partner_id": "p" if account_id == "acct" else p["id"]
        }}
    client.accounts.retrieve.side_effect = mocked_connected_account
    return db, client, p


def test_maria_br_pix_p5_checkout_signed_offline_settlement(env):
    db, client, p = use_maria_br(env)
    initial = run(pix.partner_checkout(body(), {"partner_id": "p"}))
    assert initial["amount"] == 95.0
    assert initial["discount"] == 5.0
    assert initial["platform_amount"] == 10.0
    assert initial["split_status"] == "pending"
    tx = db.payment_transactions.items[0]
    assert tx["influencer_id"] == p["id"]
    assert tx["influencer_destination"] == p["mock_stripe_account_id"]
    assert tx["partner_cents"] == 8000
    assert tx["influencer_cents"] == 500
    assert tx["platform_cents"] == 1000
    assert tx["payment_status"] == "pending"
    assert db.redemptions.items == []
    assert client.transfers.create.call_count == 0

    run(pix.settle(tx, paid()))
    assert len(db.redemptions.items) == 1
    assert db.redemptions.items[0]["influencer_id"] == p["id"]
    assert db.redemptions.items[0]["influencer"] == "Maria Eduarda"
    assert db.payment_transactions.items[0]["payment_status"] == "paid"
    assert db.payment_transactions.items[0]["split_status"] == "completed"
    transfers = client.transfers.create.call_args_list
    assert [c.kwargs["params"]["amount"] for c in transfers] == [8000, 500]
    assert transfers[1].kwargs["params"]["destination"] == p["mock_stripe_account_id"]
    assert all(r["influencer_id"] == p["id"] for r in db.redemptions.items)


def test_unverified_maria_br_referral_cannot_trigger_pix_checkout(env):
    db, client, p = use_maria_br(env)
    original = client.accounts.retrieve.side_effect
    def inactive_connected_account(account_id, **kwargs):
        record = original(account_id, **kwargs)
        if account_id == p["mock_stripe_account_id"]:
            record["payouts_enabled"] = False
            record["capabilities"] = {"transfers": "inactive"}
        return record
    client.accounts.retrieve.side_effect = inactive_connected_account
    with pytest.raises(HTTPException) as exc:
        run(pix.partner_checkout(body(), {"partner_id": "p"}))
    assert exc.value.status_code == 409
    env[1].assert_not_called()
    assert len(db.payment_transactions.items) == 0
    assert db.redemptions.items == []


def test_unverified_maria_br_connect_identity_cannot_be_assumed(env):
    db, client, p = use_maria_br(env)
    original = client.accounts.retrieve.side_effect
    def missing_owner(account_id, **kwargs):
        record = original(account_id, **kwargs)
        if account_id == p["mock_stripe_account_id"]:
            record["metadata"] = {}
        return record
    client.accounts.retrieve.side_effect = missing_owner
    with pytest.raises(HTTPException) as exc:
        run(pix.partner_checkout(body(), {"partner_id": "p"}))
    assert exc.value.status_code == 409
    env[1].assert_not_called()
    assert len(db.payment_transactions.items) == 0


def test_maria_pt_eur_p5_checkout_and_commission_only_in_mock_database(pt):
    p = profiles()["PT"]
    assert p["currency"] == "eur"
    asyncio.run(pt.db.influencers.insert_one({
        "id": p["id"], "nome": p["name"], "status": "Ativo",
        "currency": "eur", "is_test": True,
    }))
    asyncio.run(pt.db.campaigns.update_one(
        {"id": "cpt"}, {"$set": {"influencer_id": p["id"]}}
    ))
    response = request(pt.app, "POST", "/api/public/pay", json={
        "code": "EURP5", "amount": 100, "origin_url": ORIGIN,
    })
    assert response.status_code == 200, response.text
    assert response.json()["to_pay"] == 95.0
    assert response.json()["discount"] == 5.0
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 0

    # Signed webhook confirmed by real stripe-python signature verifier,
    # but signature and Stripe event are generated LOCALLY.
    event = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_test_pt_http", "payment_status": "paid",
        "currency": "eur", "amount_total": 9500, "livemode": False,
        "payment_intent": "pi_test_maria_pt", "metadata": {"kind": "coupon_pay", "coupon": "EURP5", "campaign_id": "cpt", "partner_id": "ppt"},
    }}}
    raw, headers = signed_event(event, "whsec_local_http_only")
    reply = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    assert reply.status_code == 200, reply.text
    rec = asyncio.run(pt.db.redemptions.find_one({"coupon": "EURP5"}))
    assert rec is not None
    assert rec["influencer_id"] == p["id"]
    assert rec["influencer"] == "Maria Eduarda"
    assert rec["amount"] == 100
    assert rec["discount"] == 5
    assert rec["commission"] == 5

    reply2 = request(pt.app, "POST", "/api/stripe/webhook", content=raw, headers=headers)
    assert reply2.status_code == 200
    assert asyncio.run(pt.db.redemptions.count_documents({})) == 1
    assert asyncio.run(pt.db.payment_transactions.count_documents({"session_id": "cs_test_pt_http"})) == 1
