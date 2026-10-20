"""PT dual Stripe Connect P5 TEST sandbox: signed HTTP, verified recipients, retries and refund.

No real Stripe, DB or money. All transfers and connected accounts are simulated.
"""
import asyncio
from collections import Counter

import pytest
from fastapi import HTTPException

from tests.test_payment_http_integration import pt, request, signed_event, ORIGIN
from payments import pt_split


@pytest.fixture
def dual(pt, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_" + "x"*40)
    monkeypatch.setenv("PT_SPLIT_V2_ENABLED", "true")
    asyncio.run(pt.db.partners.update_one({"id": "ppt"}, {"$set": {
        "status": "Ativo", "stripe_account_id": "acct_partner_pt_test"
    }}))
    asyncio.run(pt.db.influencers.insert_one({
        "id": "inf_pt", "status": "Ativo", "nome": "Maria Eduarda",
        "stripe_account_id": "acct_influencer_pt_test"
    }))
    asyncio.run(pt.db.campaigns.update_one({"id": "cpt"}, {"$set": {
        "influencer_id": "inf_pt"
    }}))
    remote_reversed = {"tr_partner": 0, "tr_influencer": 0}
    calls = []
    fail_once = {"role": None}
    async def fake_provider(op, *args, **kw):
        calls.append((op,args,dict(kw)))
        if op == "accounts.retrieve":
            account = args[0]
            role = "ppt" if account == "acct_partner_pt_test" else "inf_pt"
            return {
                "id": account, "country": "PT", "details_submitted": True,
                "payouts_enabled": True, "capabilities": {"transfers": "active"},
                "metadata": {"partner_id": "ppt"} if role == "ppt" else {"influencer_id": "inf_pt"},
                "requirements": {"currently_due": [], "disabled_reason": None},
            }
        if op == "payment_intents.retrieve":
            return {"status": "succeeded", "currency": "eur", "amount_received": 9500,
                    "latest_charge": "ch_test_pt"}
        if op == "transfers.create":
            role = kw["metadata"]["recipient"]
            if fail_once["role"] == role:
                fail_once["role"] = None
                raise HTTPException(503, "Simulated transient Stripe timeout")
            return {"id": "tr_"+role}
        if op == "transfers.retrieve":
            return {"amount_reversed":remote_reversed[args[0]]}
        if op == "transfers.reversals.create":
            remote_reversed[args[0]] += kw["amount"]
            return {"id": "trr_test"}
        raise AssertionError("Unexpected Stripe operation: "+op)
    monkeypatch.setattr(pt_split, "provider", fake_provider)
    return {"pt": pt, "calls": calls, "fail_once":fail_once, "reversed": remote_reversed}


def checkout(dual):
    pt=dual["pt"]
    answer=request(pt.app,"POST","/api/public/pay",json={
        "code":"EURP5","amount":100,"origin_url":ORIGIN
    })
    assert answer.status_code==200,answer.text
    assert answer.json()["to_pay"]==95
    assert answer.json()["split"] is True
    intent=pt.created.call_args.kwargs["payment_intent_data"]
    assert intent["transfer_group"].startswith("tx")
    tx=asyncio.run(pt.db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert tx["split_mode"]=="pt_separate_v2"
    assert (tx["partner_cents"],tx["influencer_cents"],tx["platform_cents"])==(8000,500,1000)
    assert tx["payment_status"]=="pending"
    return tx


def payment():
    return signed_event({"type":"checkout.session.completed","data":{"object":{
        "id":"cs_test_pt_http","payment_status":"paid","currency":"eur",
        "amount_total":9500,"livemode":False,"payment_intent":"pi_test_pt_dual",
        "metadata":{"kind":"coupon_pay","coupon":"EURP5","campaign_id":"cpt","partner_id":"ppt"}
    }}},"whsec_local_http_only")


def test_two_verified_payouts_only_after_confirmed_payment(dual):
    tx=checkout(dual)
    assert not any(x[0]=="transfers.create" for x in dual["calls"])
    raw,headers=payment()
    paid=request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers)
    assert paid.status_code==200,paid.text
    again=request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers)
    assert again.status_code==200
    transfers=[x for x in dual["calls"] if x[0]=="transfers.create"]
    assert len(transfers)==2
    assert sorted(x[2]["amount"] for x in transfers)==[500,8000]
    assert all(x[2]["source_transaction"]=="ch_test_pt" for x in transfers)
    assert {x[2]["destination"] for x in transfers}=={"acct_partner_pt_test","acct_influencer_pt_test"}
    assert len({x[2]["idempotency_key"] for x in transfers})==2
    assert asyncio.run(dual["pt"].db.redemptions.count_documents({}))==1
    tx=asyncio.run(dual["pt"].db.payment_transactions.find_one({"id":tx["id"]}))
    assert tx["split_status"]=="completed"


def test_failed_second_leg_retries_without_second_first_transfer(dual):
    checkout(dual)
    dual["fail_once"]["role"]="influencer"
    raw,headers=payment()
    first=request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers)
    assert first.status_code==503
    tx=asyncio.run(dual["pt"].db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert tx["payment_status"]=="paid"
    assert tx["split_status"]=="pending"
    assert tx["partner_transfer_id"]=="tr_partner"
    retry=request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers)
    assert retry.status_code==200,retry.text
    transfers=[x for x in dual["calls"] if x[0]=="transfers.create"]
    assert [x[2]["metadata"]["recipient"] for x in transfers]==["partner","influencer","influencer"]
    final=asyncio.run(dual["pt"].db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert final["split_status"]=="completed"
    assert asyncio.run(dual["pt"].db.redemptions.count_documents({}))==1


@pytest.mark.parametrize("bad",[
    {"payouts_enabled":False},{"details_submitted":False},
    {"capabilities":{"transfers":"inactive"}},{"country":"BR"},
    {"metadata":{}},{"requirements":{"currently_due":["company.tax_id"]}},
])
def test_unverified_influencer_cannot_start_checkout(dual, monkeypatch, bad):
    original=pt_split.provider
    async def invalid(op,*args,**kw):
        result=await original(op,*args,**kw)
        if op=="accounts.retrieve" and args[0]=="acct_influencer_pt_test":
            return {**result,**bad}
        return result
    monkeypatch.setattr(pt_split,"provider",invalid)
    result=request(dual["pt"].app,"POST","/api/public/pay",json={
        "code":"EURP5","amount":100,"origin_url":ORIGIN
    })
    assert result.status_code==409,result.text
    dual["pt"].created.assert_not_called()
    assert asyncio.run(dual["pt"].db.payment_transactions.count_documents({}))==0


def test_live_key_never_used_by_pt_split(dual,monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY","sk_live_"+"x"*40)
    response=request(dual["pt"].app,"POST","/api/public/pay",json={
        "code":"EURP5","amount":100,"origin_url":ORIGIN
    })
    assert response.status_code==503
    dual["pt"].created.assert_not_called()


def refund_event(refunded):
    return signed_event({"type":"charge.refunded","data":{"object":{
        "id":"ch_test_pt","payment_intent":"pi_test_pt_dual","currency":"eur",
        "amount":9500,"amount_refunded":refunded
    }}},"whsec_local_http_only")


def test_partial_then_full_refund_reverse_exactly_once(dual):
    checkout(dual)
    raw,headers=payment()
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    raw,headers=refund_event(4750)
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    assert dual["reversed"]=={"tr_partner":4000,"tr_influencer":250}
    raw,headers=refund_event(9500)
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    assert dual["reversed"]=={"tr_partner":8000,"tr_influencer":500}
    rows=asyncio.run(dual["pt"].db.redemptions.find({}).to_list(20))
    assert len(rows)==2
    negative=[x for x in rows if x.get("is_refund")]
    assert len(negative)==1
    assert negative[0]["amount"]==-100
    assert negative[0]["commission"]==-5
    tx=asyncio.run(dual["pt"].db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert tx["payment_status"]=="refunded"
    assert tx["manual_payout_blocked"] is True
    # Original paid webhook replay must not reopen a refunded or held account.
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=payment()[0],headers=payment()[1]).status_code==200
    tx=asyncio.run(dual["pt"].db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert tx["payment_status"]=="refunded"


def test_dispute_holds_transfers_and_commission(dual):
    checkout(dual)
    raw,headers=payment()
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    raw,headers=signed_event({"type":"charge.dispute.created","data":{"object":{
        "id":"dp_test","payment_intent":"pi_test_pt_dual"
    }}},"whsec_local_http_only")
    assert request(dual["pt"].app,"POST","/api/stripe/webhook",content=raw,headers=headers).status_code==200
    tx=asyncio.run(dual["pt"].db.payment_transactions.find_one({"session_id":"cs_test_pt_http"}))
    assert tx["payment_status"]=="disputed" and tx["dispute_hold"] is True
    rec=asyncio.run(dual["pt"].db.redemptions.find_one({"id":tx["redemption_id"]}))
    assert rec["commission"]==0 and rec["dispute_hold"] is True
