"""Payment safety regressions; MongoDB, Stripe and side effects are mocked."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline_payment_confirmation')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_offline_no_calls')
import routes_payments as pay

run = asyncio.run


@pytest.fixture
def db(monkeypatch):
    database = AsyncMongoMockClient().confirmation
    monkeypatch.setattr(pay, 'db', database)
    monkeypatch.setattr(pay, 'WEBHOOK_SECRET', 'whsec_offline')
    return database


async def transaction(db, kind='coupon_pay'):
    await db.payment_transactions.insert_one({
        'id': 'tx_offline', 'session_id': 'cs_test_offline', 'kind': kind,
        'payment_status': 'pending', 'status': 'initiated', 'user_id': None,
    })


@pytest.mark.parametrize('payment_state', ['unpaid', 'no_payment_required'])
def test_completed_checkout_does_not_confirm_unpaid_sale(db, monkeypatch, payment_state):
    async def scenario():
        await transaction(db)
        monkeypatch.setattr(pay.stripe.checkout.Session, 'retrieve', Mock(return_value=SimpleNamespace(
            payment_status=payment_state, status='complete')))
        fulfil = AsyncMock()
        monkeypatch.setattr(pay, 'fulfil', fulfil)
        result = await pay.payment_status('cs_test_offline')
        fulfil.assert_not_awaited()
        assert result['payment_status'] == 'pending'
    run(scenario())


def test_paid_checkout_still_confirms_sale(db, monkeypatch):
    async def scenario():
        await transaction(db)
        monkeypatch.setattr(pay.stripe.checkout.Session, 'retrieve', Mock(return_value=SimpleNamespace(
            payment_status='paid', status='complete', subscription=None,
            payment_intent='pi_offline', customer_details=None, customer_email=None)))
        # Isolate downstream sale/email processing; inspect confirmation dispatch.
        fulfil = AsyncMock()
        monkeypatch.setattr(pay, 'fulfil', fulfil)
        await pay.payment_status('cs_test_offline')
        fulfil.assert_awaited_once()
        assert fulfil.await_args.args[1]['stripe_payment_intent_id'] == 'pi_offline'
    run(scenario())


@pytest.mark.parametrize('event_type', ['checkout.session.completed', 'checkout.session.async_payment_succeeded'])
@pytest.mark.parametrize('payment_state', [None, 'unpaid', 'paid'])
def test_webhook_requires_explicit_paid_state(db, monkeypatch, event_type, payment_state):
    obj = {'id': 'cs_test_offline'}
    if payment_state is not None:
        obj['payment_status'] = payment_state
    monkeypatch.setattr(pay.stripe.Webhook, 'construct_event', Mock(return_value={
        'type': event_type, 'data': {'object': obj}}))
    fulfil = AsyncMock()
    monkeypatch.setattr(pay, 'fulfil', fulfil)
    request = SimpleNamespace(body=AsyncMock(return_value=b'offline'), headers={})
    assert run(pay.stripe_webhook(request)) == {'status': 'ok'}
    assert fulfil.await_count == int(payment_state == 'paid')


def test_generic_webhook_does_not_process_pix(db, monkeypatch):
    monkeypatch.setattr(pay.stripe.Webhook, 'construct_event', Mock(return_value={
        'type': 'checkout.session.completed', 'data': {'object': {
            'id': 'cs_test_offline', 'payment_status': 'paid', 'metadata': {'kind': 'pix_coupon'}}}}))
    fulfil = AsyncMock()
    monkeypatch.setattr(pay, 'fulfil', fulfil)
    request = SimpleNamespace(body=AsyncMock(return_value=b'offline'), headers={})
    assert run(pay.stripe_webhook(request))['status'] == 'ignored'
    fulfil.assert_not_awaited()


def test_generic_fulfil_cannot_create_subscription_from_pix_record(db):
    async def scenario():
        await transaction(db, 'pix_coupon')
        await pay.fulfil('cs_test_offline', {})
        assert (await db.payment_transactions.find_one({'id': 'tx_offline'}))['payment_status'] == 'pending'
        assert await db.subscriptions.count_documents({}) == 0
        assert await db.redemptions.count_documents({}) == 0
    run(scenario())


def test_generic_status_redirects_pix_to_dedicated_handler(db, monkeypatch):
    async def scenario():
        await transaction(db, 'pix_coupon')
        retrieve = Mock(side_effect=AssertionError('Wrong Stripe account queried'))
        monkeypatch.setattr(pay.stripe.checkout.Session, 'retrieve', retrieve)
        with pytest.raises(HTTPException) as error:
            await pay.payment_status('cs_test_offline')
        assert error.value.status_code == 409
        retrieve.assert_not_called()
    run(scenario())


def test_generic_expiration_cannot_overwrite_pix_state(db, monkeypatch):
    async def scenario():
        await transaction(db, 'pix_coupon')
        monkeypatch.setattr(pay.stripe.Webhook, 'construct_event', Mock(return_value={
            'type': 'checkout.session.expired', 'data': {'object': {'id': 'cs_test_offline'}}}))
        await pay.stripe_webhook(SimpleNamespace(body=AsyncMock(return_value=b'offline'), headers={}))
        assert (await db.payment_transactions.find_one({'id': 'tx_offline'}))['payment_status'] == 'pending'
    run(scenario())


def test_configuration_probe_only_reads_stripe(monkeypatch):
    client = Mock()
    client.v2.core.accounts.list.return_value = SimpleNamespace(data=[])
    monkeypatch.setattr(pay, '_v2', Mock(return_value=client))
    monkeypatch.setattr(pay.stripe.Account, 'retrieve', Mock(return_value={
        'settings': {'dashboard': {'display_name': 'Offline'}}}))
    report = pay._stripe_probe()
    assert report['account_ok'] and report['connect_enabled']
    assert report['platform_profile_ok'] is None
    client.v2.core.accounts.create.assert_not_called()
    client.v2.core.accounts.close.assert_not_called()
    assert [call[0] for call in client.mock_calls] == ['v2.core.accounts.list']
