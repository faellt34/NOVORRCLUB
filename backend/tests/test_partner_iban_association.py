"""Regression tests for partner/IBAN association; in-memory database only."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_iban_test')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline_no_calls')
import routes_payments as pay


@pytest.fixture
def db(monkeypatch):
    database = AsyncMongoMockClient().iban_test
    monkeypatch.setattr(pay, 'db', database)
    monkeypatch.setattr(pay, 'audit', AsyncMock())
    return database


@pytest.mark.parametrize('pid,owner,status', [(None, None, 400), ('', None, 400), ('missing', None, 409), ('p', 'other-user', 403)])
def test_invalid_association_never_updates_iban(db, pid, owner, status):
    async def scenario():
        await db.partners.insert_one({'id': 'same-email', 'email': 'partner@example.invalid', 'iban': 'untouched'})
        if pid == 'p': await db.partners.insert_one({'id': 'p', 'user_id': owner, 'iban': 'untouched'})
        user = {'id': 'u', 'nome': 'Test partner', 'email': 'partner@example.invalid'}
        if pid is not None: user['partner_id'] = pid
        with pytest.raises(HTTPException) as error:
            await pay.set_iban(pay.IbanIn(iban='GB82 WEST 1234 5698 7654 32'), user)
        assert error.value.status_code == status
        async for partner in db.partners.find({}): assert partner['iban'] == 'untouched'
        pay.audit.assert_not_awaited()
    asyncio.run(scenario())


@pytest.mark.parametrize('owner', ['u', None])
def test_valid_explicit_link_updates_only_target_partner(db, owner):
    async def scenario():
        partner = {'id': 'p', 'iban': 'old'}
        if owner: partner['user_id'] = owner
        await db.partners.insert_one(partner)
        await db.partners.insert_one({'id': 'other', 'iban': 'untouched'})
        result = await pay.set_iban(pay.IbanIn(iban='GB82 WEST 1234 5698 7654 32', titular=None), {'id': 'u', 'nome': 'Partner', 'partner_id': 'p'})
        assert result == {'ok': True, 'iban': 'GB82WEST12345698765432'}
        assert (await db.partners.find_one({'id': 'p'}))['iban'] == result['iban']
        assert (await db.partners.find_one({'id': 'other'}))['iban'] == 'untouched'
        pay.audit.assert_awaited_once()
    asyncio.run(scenario())


def test_association_changed_during_update_does_not_claim_success(db, monkeypatch):
    async def scenario():
        await db.partners.insert_one({'id': 'p', 'user_id': 'u', 'iban': 'untouched'})
        collection = db.partners
        monkeypatch.setattr(collection, 'update_one', AsyncMock(return_value=SimpleNamespace(matched_count=0)))
        monkeypatch.setattr(pay, 'db', SimpleNamespace(partners=collection))
        with pytest.raises(HTTPException) as error:
            await pay.set_iban(pay.IbanIn(iban='GB82WEST12345698765432'), {'id': 'u', 'nome': 'Partner', 'partner_id': 'p'})
        assert error.value.status_code == 409
        pay.audit.assert_not_awaited()
    asyncio.run(scenario())
