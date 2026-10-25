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
    accounts = {'acct_j': {'id': 'acct_j', 'country': 'BR', 'metadata': {}},
                'acct_s': {'id': 'acct_s', 'country': 'BR', 'metadata': {}},
                'acct_x': {'id': 'acct_x', 'country': 'BR', 'metadata': {'partner_id': 'p-outro'}}}
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


def seed(db, inf_acct='acct_s'):
    async def go():
        await db.campaigns.insert_one({'id': 'c1', 'cupom': 'SHEYSO-7182', 'parceiro_id': 'p-j', 'influencer_id': 'if-s'})
        await db.partners.insert_one({'id': 'p-j', 'nome': 'Josicleide', 'pix_stripe_account_id': 'acct_j'})
        await db.influencers.insert_one({'id': 'if-s', 'nome': 'Sheyson', 'pix_stripe_account_id': inf_acct})
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
