"""Offline: dangling links are repairable; valid links and explicit currency mismatches are never overridden."""
import asyncio
import os
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_assoc_repairs')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline')
import routes_admin as admin

run = asyncio.run
ADMIN = {'id': 'admin', 'nome': 'Admin'}


@pytest.fixture
def db(monkeypatch):
    db = AsyncMongoMockClient().repairs
    monkeypatch.setattr(admin, 'db', db)
    monkeypatch.setattr(admin, 'audit', AsyncMock())
    return db


async def seed(db, **user):
    await db.users.insert_one({'id': 'paulo', 'role': 'partner', 'email': 'p@example.invalid', **user})
    await db.partners.insert_one({'id': 'maraca', 'nome': 'Maraca', 'currency': 'brl', 'status': 'Ativo', 'iban': 'keep', 'stripe_account_id': 'acct_keep'})


def test_missing_currency_is_inherited_from_establishment_and_audited(db):
    async def scenario():
        await seed(db)
        res = await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        user = await db.users.find_one({'id': 'paulo'})
        assert user['partner_id'] == 'maraca' and user['currency'] == 'brl'
        assert any('moeda' in n for n in res['reparacoes'])
        assert 'reparação' in admin.audit.await_args.args[1]
        partner = await db.partners.find_one({'id': 'maraca'})
        assert partner['iban'] == 'keep' and partner['stripe_account_id'] == 'acct_keep' and partner['currency'] == 'brl'
    run(scenario())


def test_explicit_currency_mismatch_still_blocks(db):
    async def scenario():
        await seed(db, currency='eur')
        with pytest.raises(HTTPException) as e: await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        assert e.value.status_code == 409
        assert (await db.users.find_one({'id': 'paulo'})).get('partner_id') is None
    run(scenario())


def test_dangling_partner_id_on_account_is_repaired(db):
    async def scenario():
        await seed(db, currency='brl', partner_id='p-apagado')
        res = await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        assert (await db.users.find_one({'id': 'paulo'}))['partner_id'] == 'maraca'
        assert any('p-apagado' in n for n in res['reparacoes'])
    run(scenario())


def test_dangling_user_id_on_establishment_is_repaired(db):
    async def scenario():
        await seed(db, currency='brl')
        await db.partners.update_one({'id': 'maraca'}, {'$set': {'user_id': 'usr-apagado'}})
        res = await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        assert (await db.partners.find_one({'id': 'maraca'}))['user_id'] == 'paulo'
        assert any('usr-apagado' in n for n in res['reparacoes'])
    run(scenario())


def test_valid_links_are_never_swapped(db):
    async def scenario():
        await seed(db, currency='brl', partner_id='outro')
        await db.partners.insert_one({'id': 'outro', 'nome': 'Outro', 'status': 'Ativo'})
        with pytest.raises(HTTPException): await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        await db.users.update_one({'id': 'paulo'}, {'$unset': {'partner_id': ''}})
        await db.users.insert_one({'id': 'dono', 'role': 'partner', 'currency': 'brl'})
        await db.partners.update_one({'id': 'maraca'}, {'$set': {'user_id': 'dono'}})
        with pytest.raises(HTTPException): await admin.associate_partner_account('maraca', admin.PartnerAccountIn(user_id='paulo'), ADMIN)
        assert (await db.partners.find_one({'id': 'maraca'}))['user_id'] == 'dono'
        admin.audit.assert_not_awaited()
    run(scenario())
