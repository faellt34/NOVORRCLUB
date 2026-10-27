"""Offline (Stripe mocked) P5 Portugal: MB WAY/card eligibility, paid webhook → per-beneficiary transfers, 5/80/5/10 rule."""
import asyncio
import os
from unittest.mock import AsyncMock, patch
import pytest
import stripe
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_p5_pt')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_live_pt_abcdefghijklmnop')
import pt_split
import p5_checkout as p5

ENV = {'STRIPE_SECRET_KEY': 'sk_live_pt_abcdefghijklmnop', 'PT_SPLIT_ENABLED': 'true', 'PT_SPLIT_LIVE_ENABLED': 'true',
       'PT_SPLIT_AUTO_TRANSFER': 'true', 'PAYMENT_ALLOWED_ORIGINS': 'https://rrclub.online', 'P5_ENABLED': 'true', 'P5_EUR_ENABLED': 'true'}


def pt_account(acct_id, **meta):
    return {'id': acct_id, 'country': 'PT', 'payouts_enabled': True, 'capabilities': {'transfers': 'active'}, 'requirements': {}, 'metadata': meta}


@pytest.fixture
def world(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    db = AsyncMongoMockClient().p5pt
    monkeypatch.setattr(pt_split, 'db', db); monkeypatch.setattr(p5, 'db', db)
    import core; monkeypatch.setattr(core, 'audit', AsyncMock()); monkeypatch.setattr(core, 'db', db)
    accounts = {'acct_p': pt_account('acct_p', partner_id='p-pt'), 'acct_i': {**pt_account('acct_i', influencer_id='if-pt'), 'payouts_enabled': False,
                'requirements': {'currently_due': ['external_account']}}}
    transfers = []
    monkeypatch.setattr(stripe.Account, 'retrieve', lambda acct_id=None, **kw: accounts[acct_id])
    monkeypatch.setattr(stripe.checkout.Session, 'retrieve', lambda sid, **kw: {'id': sid, 'payment_status': 'paid', 'currency': 'eur', 'amount_total': 1900,
                        'payment_intent': 'pi_1', 'metadata': {'p5_charge_id': 'p5-pt-1', 'partner_id': 'p-pt', 'influencer_id': 'if-pt'}})
    monkeypatch.setattr(stripe.PaymentIntent, 'retrieve', lambda pid, **kw: {'status': 'succeeded', 'currency': 'eur', 'amount': 1900, 'latest_charge': 'ch_1'})
    monkeypatch.setattr(stripe.Charge, 'retrieve', lambda cid, **kw: {'id': cid, 'paid': True, 'currency': 'eur', 'amount': 1900, 'refunded': False, 'disputed': False, 'amount_refunded': 0})
    monkeypatch.setattr(stripe.Transfer, 'list', lambda **kw: {'data': list(transfers)})
    def create_transfer(**kw):
        t = {'id': 'tr_' + kw['destination'], 'destination': kw['destination'], 'amount': kw['amount'], 'source_transaction': kw['source_transaction'],
             'metadata': kw['metadata'], 'reversed': False, 'amount_reversed': 0}
        transfers.append(t); return t
    monkeypatch.setattr(stripe.Transfer, 'create', create_transfer)
    async def seed():
        await db.partners.insert_one({'id': 'p-pt', 'nome': 'Hotel PT', 'currency': 'eur', 'status': 'Ativo', 'stripe_account_id': 'acct_p'})
        await db.influencers.insert_one({'id': 'if-pt', 'nome': 'Creator PT', 'currency': 'eur', 'status': 'Ativo', 'stripe_account_id': 'acct_i'})
        await db.payment_transactions.insert_one({'session_id': 'cs_1', 'currency': 'eur', 'kind': 'coupon_pay', 'split_version': pt_split.VERSION, 'payment_status': 'paid',
                                                  'p5_charge_id': 'p5-pt-1', 'partner_id': 'p-pt', 'influencer_id': 'if-pt', 'gross_minor': 2000, 'amount': 19.0,
                                                  'partner_destination': 'acct_p', 'influencer_destination': 'acct_i'})
    asyncio.run(seed())
    return db, accounts, transfers


def test_quote_rule_5_80_5_10():
    q = pt_split.quote(2000)
    assert (q['discount_minor'], q['payment_minor'], q['partner_minor'], q['influencer_minor'], q['platform_minor']) == (100, 1900, 1600, 100, 200)
    q = pt_split.quote(100)
    assert q['partner_minor'] + q['influencer_minor'] + q['platform_minor'] == q['payment_minor'] == 95


def test_partner_paid_even_when_influencer_incomplete_then_retry(world):
    db, accounts, transfers = world
    res = asyncio.run(pt_split.settle_new_p5_payment('cs_1'))
    assert res['status'] == 'partially_transferred' and res['transfers'] == {'partner': 'tr_acct_p'}
    assert res['held']['influencer'] == 'connect_onboarding_or_transfers_pending'
    assert [t['amount'] for t in transfers] == [1600]
    # webhook replay: no duplicate partner transfer
    asyncio.run(pt_split.settle_new_p5_payment('cs_1'))
    assert len(transfers) == 1
    # influencer finishes onboarding → admin retry pays the held 5%
    accounts['acct_i']['payouts_enabled'] = True; accounts['acct_i']['requirements'] = {}
    res = asyncio.run(pt_split.settle_new_p5_payment('cs_1'))
    assert res['status'] == 'transferred_to_connect' and res['transfers'] == {'partner': 'tr_acct_p', 'influencer': 'tr_acct_i'}
    assert sorted(t['amount'] for t in transfers) == [100, 1600]
    tx = asyncio.run(db.payment_transactions.find_one({'session_id': 'cs_1'}))
    assert tx['pt_split_status'] == 'transferred_to_connect' and tx['influencer_transfer_id'] == 'tr_acct_i'
    # fully settled: idempotent, nothing new
    asyncio.run(pt_split.settle_new_p5_payment('cs_1'))
    assert len(transfers) == 2


def test_account_not_bound_to_record_is_held(world):
    db, accounts, transfers = world
    accounts['acct_p']['metadata'] = {'partner_id': 'p-other'}
    res = asyncio.run(pt_split.settle_new_p5_payment('cs_1'))
    assert res['status'] == 'held' and res['held']['partner'] == 'account_id_binding_mismatch'
    assert transfers == []


def test_checkout_falls_back_to_card_when_mbway_not_eligible(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    calls = []
    def create(**kw):
        calls.append(kw['payment_method_types'])
        if 'mb_way' in kw['payment_method_types']:
            raise stripe.error.InvalidRequestError('The payment method type "mb_way" is invalid', 'payment_method_types')
        return {'id': 'cs_card', 'url': 'https://checkout.stripe.com/c/pay/cs_card'}
    monkeypatch.setattr(stripe.checkout.Session, 'create', create)
    rec = {'id': 'p5-x', 'campaign_id': 'c', 'partner_id': 'p', 'influencer_id': 'i', 'coupon': 'PT-1', 'commission_percent_snapshot': 5, 'net_minor': 1900}
    session, methods = p5._pt_stripe_checkout(rec, {'nome': 'Camp'}, {'nome': 'Hotel'}, 'https://rrclub.online', None)
    assert calls == [['card', 'mb_way'], ['card']] and methods == 'card,wallets' and session['id'] == 'cs_card'


def test_checkout_keeps_mbway_when_eligible(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: {'id': 'cs_mb', 'url': 'u', 'pm': kw['payment_method_types']})
    rec = {'id': 'p5-y', 'campaign_id': 'c', 'partner_id': 'p', 'influencer_id': 'i', 'coupon': 'PT-1', 'commission_percent_snapshot': 5, 'net_minor': 1900}
    session, methods = p5._pt_stripe_checkout(rec, {'nome': 'Camp'}, {'nome': 'Hotel'}, 'https://rrclub.online', 'a@b.pt')
    assert session['pm'] == ['card', 'mb_way'] and methods == 'card,mb_way,wallets'
