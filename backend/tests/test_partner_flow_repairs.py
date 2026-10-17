"""Offline regressions. Provider calls are mocks; no production data or charges."""
import asyncio
import os
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_partner_flow')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline')
import routes_admin as admin
import routes_data as data
import routes_payments as pay

run = asyncio.run


@pytest.fixture
def db(monkeypatch):
    db = AsyncMongoMockClient().flows
    for module in (admin, data, pay): monkeypatch.setattr(module, 'db', db)
    monkeypatch.setattr(admin, 'audit', AsyncMock())
    monkeypatch.setattr(pay, 'audit', AsyncMock())
    monkeypatch.setattr(pay, '_connect_create', Mock(side_effect=AssertionError('Unexpected Stripe creation')))
    monkeypatch.setattr(pay, '_connect_link', Mock(side_effect=AssertionError('Unexpected Stripe link')))
    monkeypatch.setenv('FRONTEND_URL', 'https://rrclub.online')
    return db


async def records(db):
    await db.users.insert_one({'id': 'u', 'role': 'partner', 'currency': 'eur', 'email': 'test@example.invalid'})
    await db.partners.insert_one({'id': 'p', 'nome': 'Estabelecimento', 'currency': 'eur', 'status': 'Ativo', 'stripe_account_id': 'acct_existing', 'iban': 'unchanged'})


def test_explicit_association_preserves_financial_settings_and_is_idempotent(db):
    async def scenario():
        await records(db)
        for _ in range(2): await admin.associate_partner_account('p', admin.PartnerAccountIn(user_id='u'), {'id': 'admin', 'nome': 'Admin'})
        partner = await db.partners.find_one({'id': 'p'})
        assert partner['user_id'] == 'u' and partner['stripe_account_id'] == 'acct_existing' and partner['iban'] == 'unchanged'
        assert (await db.users.find_one({'id': 'u'}))['partner_id'] == 'p'
    run(scenario())


@pytest.mark.parametrize('conflict', ['owner', 'account', 'role', 'currency', 'other_user'])
def test_association_rejects_ambiguous_or_owned_records(db, conflict):
    async def scenario():
        await records(db)
        if conflict == 'owner': await db.partners.update_one({'id': 'p'}, {'$set': {'user_id': 'other'}})
        if conflict == 'account': await db.users.update_one({'id': 'u'}, {'$set': {'partner_id': 'other'}})
        if conflict == 'role': await db.users.update_one({'id': 'u'}, {'$set': {'role': 'admin'}})
        if conflict == 'currency': await db.users.update_one({'id': 'u'}, {'$set': {'currency': 'brl'}})
        if conflict == 'other_user': await db.users.insert_one({'id': 'other', 'partner_id': 'p'})
        with pytest.raises(HTTPException): await admin.associate_partner_account('p', admin.PartnerAccountIn(user_id='u'), {})
        assert (await db.partners.find_one({'id': 'p'}))['iban'] == 'unchanged'
        admin.audit.assert_not_awaited()
    run(scenario())


def test_concurrent_accounts_cannot_claim_same_business(db):
    async def scenario():
        await records(db)
        await db.users.insert_one({'id': 'u2', 'role': 'partner', 'currency': 'eur'})
        results = await asyncio.gather(*[admin.associate_partner_account('p', admin.PartnerAccountIn(user_id=uid), {}) for uid in ('u', 'u2')], return_exceptions=True)
        assert sum(isinstance(result, dict) for result in results) == 1
        assert await db.users.count_documents({'partner_id': 'p'}) == 1
        partner = await db.partners.find_one({'id': 'p'})
        assert (await db.users.find_one({'id': partner['user_id']}))['partner_id'] == 'p'
    run(scenario())


@pytest.mark.parametrize('operation', ['preview', 'redeem', 'dashboard', 'connect'])
def test_missing_partner_is_blocked_before_any_lookup_or_provider_action(db, operation):
    async def scenario():
        # Matching email is deliberately insufficient to gain business access.
        await db.partners.insert_one({'id': 'p', 'email': 'test@example.invalid'})
        user = {'id': 'u', 'nome': 'Test', 'email': 'test@example.invalid'}
        calls = {'preview': lambda: data.preview_coupon('LUCAS2027', user), 'redeem': lambda: data.redeem(data.RedeemIn(code='LUCAS2027', amount=2, idempotency_key='test'), user), 'dashboard': lambda: data.partner_dashboard(user, 'eur'), 'connect': lambda: pay.connect_onboard({}, user)}
        with pytest.raises(HTTPException) as error: await calls[operation]()
        assert error.value.status_code == 400
        assert await db.redemptions.count_documents({}) == 0
        pay._connect_create.assert_not_called()
    run(scenario())


def test_coupon_lookup_is_scoped_to_explicit_partner(db):
    async def scenario():
        await db.partners.insert_many([{'id': 'p'}, {'id': 'other'}])
        await db.campaigns.insert_one({'id': 'c', 'cupom': 'LUCAS2027', 'parceiro_id': 'p'})
        assert await data.preview_coupon('lucas2027', {'id': 'u', 'partner_id': 'other'}) is None
        assert (await data.preview_coupon('lucas2027', {'id': 'u', 'partner_id': 'p'}))['id'] == 'c'
    run(scenario())


def test_redemption_idempotency_does_not_expose_another_business(db):
    async def scenario():
        await db.partners.insert_one({'id': 'p'})
        await db.redemptions.insert_one({'partner_id': 'other', 'coupon': 'LUCAS2027', 'amount': 2, 'idempotency_key': 'known'})
        with pytest.raises(HTTPException) as error: await data.redeem(data.RedeemIn(code='LUCAS2027', amount=2, idempotency_key='known'), {'id': 'u', 'partner_id': 'p'})
        assert error.value.status_code == 409
    run(scenario())


def test_failed_stripe_read_does_not_overwrite_cached_flags(db, monkeypatch):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'stripe_account_id': 'acct_existing', 'stripe_charges_enabled': True, 'stripe_payouts_enabled': True})
        monkeypatch.setattr(pay, '_connect_status', Mock(side_effect=RuntimeError('offline failure')))
        result = await pay.connect_status({'id': 'u', 'partner_id': 'p'})
        assert result['status_verified'] is False and result['charges_enabled'] is None
        record = await db.partners.find_one({'id': 'p'})
        assert record['stripe_charges_enabled'] is True and record['stripe_payouts_enabled'] is True
    run(scenario())


def test_existing_connect_account_is_reused(db, monkeypatch):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'nome': 'Maraca', 'stripe_account_id': 'acct_existing'})
        monkeypatch.setattr(pay, '_connect_link', Mock(return_value=type('Link', (), {'url': 'https://connect.stripe.com/test'})()))
        result = await pay.connect_onboard({'origin_url': 'https://rrclub.online'}, {'id': 'u', 'nome': 'Partner', 'email': 'test@example.invalid', 'partner_id': 'p'})
        assert result['account_id'] == 'acct_existing'
        pay._connect_create.assert_not_called()
    run(scenario())


def test_connect_rejects_wrong_return_origin_and_foreign_metadata(db, monkeypatch):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'stripe_account_id': 'acct_existing'})
        with pytest.raises(HTTPException) as error: await pay.connect_onboard({'origin_url': 'https://evil.invalid'}, {'id': 'u', 'partner_id': 'p'})
        assert error.value.status_code == 400
        monkeypatch.setattr(pay, '_connect_status', Mock(return_value={'partner_id': 'other', 'charges_enabled': True, 'payouts_enabled': True}))
        with pytest.raises(HTTPException) as error: await pay.connect_status({'id': 'u', 'partner_id': 'p'})
        assert error.value.status_code == 409
        assert 'stripe_charges_enabled' not in await db.partners.find_one({'id': 'p'})
    run(scenario())


def test_one_account_cannot_claim_two_establishments_concurrently(db):
    async def scenario():
        await records(db)
        await db.partners.insert_one({'id': 'p2', 'currency': 'eur'})
        results = await asyncio.gather(*[admin.associate_partner_account(pid, admin.PartnerAccountIn(user_id='u'), {}) for pid in ('p', 'p2')], return_exceptions=True)
        assert sum(isinstance(result, dict) for result in results) == 1
        assert await db.partners.count_documents({'user_id': 'u'}) == 1
    run(scenario())


def test_association_endpoint_requires_administrator():
    import core
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(admin.router, prefix='/api')
    app.dependency_overrides[core.get_current_user] = lambda: {'id': 'u', 'role': 'partner'}
    with TestClient(app) as client:
        assert client.post('/api/admin/parceiros/p/conta', json={'user_id': 'u'}).status_code == 403


def test_verified_connect_sync_persists_time_and_capabilities(db, monkeypatch):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'stripe_account_id': 'acct_existing'})
        monkeypatch.setattr(pay, '_connect_status', Mock(return_value={'partner_id': 'p', 'charges_enabled': True, 'payouts_enabled': True}))
        result = await pay.connect_status({'id': 'u', 'partner_id': 'p'})
        saved = await db.partners.find_one({'id': 'p'})
        assert result['status_verified'] and saved['stripe_status_synced_at'] == result['last_synced_at']
        assert saved['stripe_payouts_enabled'] is True
    run(scenario())


def test_repeated_account_creation_uses_same_idempotency_key(monkeypatch):
    from types import SimpleNamespace as NS
    create = Mock(return_value=NS(id='acct_same'))
    monkeypatch.setattr(pay, '_v2', lambda: NS(v2=NS(core=NS(accounts=NS(create=create)))))
    pay._connect_create('test@example.invalid', 'Partner', 'p')
    pay._connect_create('test@example.invalid', 'Partner', 'p')
    assert [call.kwargs['options']['idempotency_key'] for call in create.call_args_list] == ['rrclub-connect-p', 'rrclub-connect-p']


def test_invalid_iban_checksum_is_rejected_before_writing(db):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'iban': 'unchanged'})
        with pytest.raises(HTTPException) as error:
            await pay.set_iban(pay.IbanIn(iban='GB83 WEST 1234 5698 7654 32'), {'id': 'u', 'partner_id': 'p', 'nome': 'Partner'})
        assert error.value.status_code == 400
        assert (await db.partners.find_one({'id': 'p'}))['iban'] == 'unchanged'
    run(scenario())
