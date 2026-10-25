"""Offline: legacy BR Connect accounts with empty metadata get the stored owner stamped; bound accounts are never re-bound."""
import asyncio
import os
from unittest.mock import AsyncMock
import pytest
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_pix_reconcile')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline')
import routes_pix as pix

ADMIN = {'id': 'admin', 'nome': 'Admin'}


@pytest.fixture
def env(monkeypatch):
    db = AsyncMongoMockClient().pix
    monkeypatch.setattr(pix, 'db', db)
    calls = []
    accounts = {'acct_j': {'id': 'acct_j', 'country': 'BR', 'metadata': {}, 'email': 'j@x.br', 'charges_enabled': True, 'payouts_enabled': True, 'business_profile': {'name': 'Josicleide Farias dos Santos Farias'}},
                'acct_1': {'id': 'acct_1', 'country': 'BR', 'metadata': {}, 'email': 'j@x.br'},
                'acct_d': {'id': 'acct_d', 'country': 'BR', 'metadata': {}, 'email': 'other@x.br', 'individual': {'first_name': 'Sheyson', 'last_name': '', 'verification': {'status': 'unverified'}}},
                'acct_s': {'id': 'acct_s', 'country': 'BR', 'metadata': {}, 'email': 'other@x.br', 'charges_enabled': True, 'payouts_enabled': True, 'individual': {'first_name': 'Sheyson', 'last_name': 'Torres'}},
                'acct_x': {'id': 'acct_x', 'country': 'BR', 'metadata': {'partner_id': 'p-outro'}, 'email': 'j@x.br'},
                'acct_n': {'id': 'acct_n', 'country': 'BR', 'metadata': {}, 'email': 'nobody@x.br', 'business_profile': {'name': 'Loja Z'}}}
    async def provider(op, *a, **kw):
        calls.append((op, a, kw))
        if op == 'accounts.retrieve':
            return accounts[a[0]]
        if op == 'accounts.update':
            accounts[a[0]]['metadata'].update(kw['metadata']); return accounts[a[0]]
        raise AssertionError(op)
    monkeypatch.setattr(pix, 'provider', provider)
    import core
    monkeypatch.setattr(core, 'audit', AsyncMock())
    return db, calls, accounts, core.audit


def seed(db, inf_acct='acct_s', partner_acct='acct_j'):
    async def go():
        await db.campaigns.insert_one({'id': 'c1', 'cupom': 'SHEYSO-7182', 'parceiro_id': 'p-j', 'influencer_id': 'if-s'})
        await db.users.insert_one({'id': 'u-j', 'email': 'J@x.br'})
        await db.partners.insert_one({'id': 'p-j', 'nome': 'Josicleide Farias dos Santos', 'pix_stripe_account_id': partner_acct, 'user_id': 'u-j'})
        await db.influencers.insert_one({'id': 'if-s', 'nome': 'Sheyson da Silva Torres', 'pix_stripe_account_id': inf_acct, 'user_id': 'u-s'})
    asyncio.run(go())


def test_empty_metadata_is_stamped_with_stored_owner_and_audited(env):
    db, calls, accounts, audit = env
    seed(db)
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res['result'] == {'partner': 'associado agora', 'influencer': 'associado agora'}
    assert accounts['acct_j']['metadata'] == {'partner_id': 'p-j'}
    assert accounts['acct_s']['metadata'] == {'influencer_id': 'if-s'}
    assert audit.await_count == 2
    assert all(op in ('accounts.retrieve', 'accounts.update') for op, _, _ in calls)
    res2 = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res2['result'] == {'partner': 'já associado', 'influencer': 'já associado'}


def test_account_bound_to_someone_else_is_never_rebound(env):
    db, calls, accounts, audit = env
    seed(db, inf_acct='acct_x')
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res['result']['influencer'].startswith('conflito')
    assert accounts['acct_x']['metadata'] == {'partner_id': 'p-outro'}
    assert not any(op == 'accounts.update' and a[0] == 'acct_x' for op, a, _ in calls)


def test_receiving_status_passes_after_stamp(env):
    db, calls, accounts, audit = env
    seed(db)
    asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    acct = {**accounts['acct_j'], 'charges_enabled': True, 'payouts_enabled': True,
            'capabilities': {'transfers': 'active'}, 'settings': {'payouts': {'schedule': {'interval': 'daily'}}}}
    status = pix.receiving_status(acct, {'id': 'p-j', 'pix_stripe_account_id': 'acct_j'}, 'partner')
    assert status['receiving_ready'] is True


def test_no_independent_evidence_is_not_reconciled(env):
    db, calls, accounts, audit = env
    seed(db, inf_acct='acct_n')
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res['result']['influencer'].startswith('evidência insuficiente')
    assert accounts['acct_n']['metadata'] == {}


def test_single_proof_is_not_enough(env):
    db, calls, accounts, audit = env
    seed(db, partner_acct='acct_1')
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert res['result']['partner'].startswith('evidência insuficiente') and 'pontos=1' in res['result']['partner']
    assert accounts['acct_1']['metadata'] == {}


def test_account_shared_by_two_records_is_not_reconciled(env):
    db, calls, accounts, audit = env
    seed(db, inf_acct='acct_d')
    asyncio.run(db.partners.insert_one({'id': 'p-dup', 'nome': 'Dup', 'pix_stripe_account_id': 'acct_d'}))
    res = asyncio.run(pix.recipients_reconcile('c1', ADMIN))
    assert 'conta_unica=False' in res['result']['influencer']
    assert accounts['acct_d']['metadata'] == {}
