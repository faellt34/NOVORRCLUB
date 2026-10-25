"""Integration (offline, Stripe mocked): P5 BRL checkout returns a Pix checkout URL once both recipients are apt and owner metadata is stamped."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_p5_pix_checkout')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline')
import routes_pix as pix
import p5_checkout as p5

ADMIN = {'id': 'admin', 'nome': 'Admin'}
PIX_ENV = {'PIX_ENABLED': 'true', 'PIX_STRIPE_PLATFORM_COUNTRY': 'BR', 'PIX_STRIPE_SECRET_KEY': 'sk_live_br_abcdefghijklmnop',
           'PIX_STRIPE_WEBHOOK_SECRET': 'whsec_x', 'PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION': 'pmc_pix', 'STRIPE_SECRET_KEY': 'sk_live_pt_abcdefghijklmnop',
           'PAYMENT_ALLOWED_ORIGINS': 'https://rrclub.online', 'P5_ENABLED': 'true', 'P5_BRL_ENABLED': 'true'}


def apt(acct_id, email, **extra):
    return {'id': acct_id, 'country': 'BR', 'default_currency': 'brl', 'email': email, 'metadata': {}, 'charges_enabled': True, 'payouts_enabled': True,
            'capabilities': {'transfers': 'active', 'pix_payments': 'active'}, 'settings': {'payouts': {'schedule': {'interval': 'daily'}}}, **extra}


@pytest.fixture
def world(monkeypatch):
    for k, v in PIX_ENV.items():
        monkeypatch.setenv(k, v)
    db = AsyncMongoMockClient().p5pix
    monkeypatch.setattr(pix, 'db', db); monkeypatch.setattr(p5, 'db', db)
    import core; monkeypatch.setattr(core, 'audit', AsyncMock())
    accounts = {'acct_j': apt('acct_j', 'josi@x.br'), 'acct_s': apt('acct_s', 'shey@x.br')}
    platform = {'country': 'BR', 'default_currency': 'brl', 'charges_enabled': True, 'payouts_enabled': True,
                'settings': {'payouts': {'schedule': {'interval': 'daily'}}}, 'capabilities': {'pix_payments': 'active'}}
    config = {'id': 'pmc_pix', 'active': True, 'livemode': True, 'pix': {'available': True, 'display_preference': {'value': 'on'}},
              'card': {'available': True, 'display_preference': {'value': 'off'}}}
    calls = []
    async def provider(op, *a, **kw):
        calls.append(op)
        if op == 'accounts.retrieve_current': return platform
        if op == 'payment_method_configurations.retrieve': return config
        if op == 'accounts.retrieve': return accounts[a[0]]
        if op == 'accounts.update': accounts[a[0]]['metadata'].update(kw['metadata']); return accounts[a[0]]
        if op == 'checkout.sessions.create':
            class S(dict):
                __getattr__ = dict.get
            return S(id='cs_live_pix_1', url='https://checkout.stripe.com/c/pay/cs_live_pix_1', payment_status='unpaid', payment_method_types=['pix'])
        raise AssertionError(op)
    monkeypatch.setattr(pix, 'provider', provider)
    async def seed():
        await db.users.insert_many([{'id': 'u-j', 'email': 'josi@x.br', 'role': 'partner'}, {'id': 'u-s', 'email': 'shey@x.br', 'role': 'influencer'}])
        await db.partners.insert_one({'id': 'p-j', 'nome': 'Josicleide', 'currency': 'brl', 'status': 'Ativo', 'user_id': 'u-j', 'pix_stripe_account_id': 'acct_j'})
        await db.influencers.insert_one({'id': 'if-s', 'nome': 'Sheyson', 'status': 'Ativo', 'user_id': 'u-s', 'pix_stripe_account_id': 'acct_s'})
        await db.campaigns.insert_one({'id': 'c1', 'nome': 'SHEYSON', 'cupom': 'SHEYSO-7182', 'parceiro_id': 'p-j', 'influencer_id': 'if-s', 'currency': 'brl', 'desconto': 5, 'comissao': 5, 'status': 'Ativa', 'validade': '2030-01-01'})
        await db.p5_charges.insert_one({'id': 'p5-integ-0001', 'campaign_id': 'c1', 'partner_id': 'p-j', 'influencer_id': 'if-s', 'coupon': 'SHEYSO-7182', 'currency': 'brl',
                                        'gross_minor': 10000, 'discount_minor': 500, 'net_minor': 9500, 'commission_percent_snapshot': 5, 'status': 'pending',
                                        'scan_ref': 'ref1', 'session_token_hash': 'h', 'expires_at': '2030-01-01T00:00:00+00:00'})
    asyncio.run(seed())
    return db, accounts, calls


def test_blocked_before_reconcile_then_pix_url_after(world, monkeypatch):
    db, accounts, calls = world
    monkeypatch.setattr(p5, 'owned_session', AsyncMock(return_value={'scan_ref': 'ref1'}))
    body = p5.CheckoutCharge(charge_id='p5-integ-0001', origin_url='https://rrclub.online')
    before = asyncio.run(p5.checkout_charge(body, 'x' * 40))
    assert before.get('status') == 'awaiting_connect' and before.get('financial_state') == 'connect_brasil_associacao_pendente'
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res['result'] == {'partner': 'associado agora', 'influencer': 'associado agora'}
    after = asyncio.run(p5.checkout_charge(body, 'x' * 40))
    assert after['checkout_url'].startswith('https://checkout.stripe.com/') and after['pix_request_id']
    assert 'checkout.sessions.create' in calls
    rec = asyncio.run(db.p5_charges.find_one({'id': 'p5-integ-0001'}))
    assert rec['status'] == 'checkout' and rec['checkout_url'] == after['checkout_url']
