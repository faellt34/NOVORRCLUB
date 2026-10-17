"""Offline regression tests: no calls to Stripe, bank, email or AI."""
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from tests.test_pix_service import env, run, body, paid
import routes_pix as pix
from payments.pix.checks import WEBHOOK_EVENTS, receiving_status


def test_missing_configuration_diagnostic_never_calls_stripe(env, monkeypatch):
    monkeypatch.delenv('PIX_STRIPE_SECRET_KEY', raising=False)
    report = run(pix.provider_readiness({'role':'admin'}))
    assert not report['provider_verified'] and 'api_key' in report['missing_configuration']
    pix.stripe.StripeClient.assert_not_called()


def test_diagnostic_reads_provider_without_mutations(env):
    client = pix.stripe_client().v1
    client.webhook_endpoints.list.return_value = {'data':[{
        'url':'https://rrclub.online/api/stripe/pix/webhook','status':'enabled','enabled_events':list(WEBHOOK_EVENTS)}]}
    report = run(pix.provider_readiness({'role':'admin'}))
    assert report['provider_verified']
    assert report['livemode'] is False
    assert all(not call[0].endswith(('.create', '.update', '.delete')) for call in client.mock_calls)


@pytest.mark.parametrize('change', ['portugal','pix_off','mixed_checkout','wrong_mode','no_webhook'])
def test_diagnostic_explains_actual_blockers(env, change):
    client = pix.stripe_client().v1
    client.webhook_endpoints.list.return_value = {'data':[{
        'url':'https://rrclub.online/api/stripe/pix/webhook','status':'enabled','enabled_events':['*']}]}
    if change == 'portugal': client.accounts.retrieve_current.return_value['country'] = 'PT'
    if change == 'pix_off': client.accounts.retrieve_current.return_value['capabilities']['pix_payments'] = 'inactive'
    if change == 'mixed_checkout': client.payment_method_configurations.retrieve.return_value['card'] = {'available':True,'display_preference':{'value':'on'}}
    if change == 'wrong_mode': client.payment_method_configurations.retrieve.return_value['livemode'] = True
    if change == 'no_webhook': client.webhook_endpoints.list.return_value = {'data':[]}
    report = run(pix.provider_readiness({'role':'admin'}))
    assert report['provider_verified'] is False
    client.checkout.sessions.create.assert_not_called()
    if change != 'no_webhook':
        with pytest.raises(HTTPException): run(pix.partner_checkout(body(), {'partner_id':'p'}))
        client.checkout.sessions.create.assert_not_called()


def test_transfer_readiness_does_not_require_merchant_card_capability():
    status = receiving_status({'country':'BR','charges_enabled':False,'payouts_enabled':True,
        'capabilities':{'transfers':'active'},'settings':{'payouts':{'schedule':{'interval':'daily'}}},'metadata':{'partner_id':'p'}}, {'id':'p'})
    assert status['receiving_ready'] and not status['charges_enabled']


def test_wrong_recipient_metadata_is_rejected(env):
    pix.stripe_client().v1.accounts.retrieve.return_value['metadata'] = {'partner_id':'someone_else'}
    with pytest.raises(HTTPException): run(pix.partner_checkout(body(), {'partner_id':'p'}))
    env[1].assert_not_called()


def test_same_recipient_for_both_shares_is_rejected(env):
    env[0].influencers.items[0]['pix_stripe_account_id'] = 'acct'
    with pytest.raises(HTTPException): run(pix.partner_checkout(body(), {'partner_id':'p'}))
    env[1].assert_not_called()


def test_suspended_partner_cannot_generate_pix(env):
    env[0].partners.items[0]['status'] = 'Suspenso'
    with pytest.raises(HTTPException): run(pix.partner_checkout(body(), {'partner_id':'p'}))
    env[1].assert_not_called()


@pytest.mark.parametrize('change',['metadata','session'])
def test_confirmation_must_match_request_before_creating_sale(env, change):
    run(pix.partner_checkout(body(), {'partner_id':'p'}))
    session = paid()
    if change == 'metadata': session['metadata']['request_id'] = 'other'
    else: session['id'] = 'cs_other'
    with pytest.raises(HTTPException): run(pix.settle(env[0].payment_transactions.items[0], session))
    assert not env[0].redemptions.items


def test_provider_timeout_keeps_stored_recipient_state(env, monkeypatch):
    monkeypatch.setattr(pix, 'provider', AsyncMock(side_effect=HTTPException(502,'Indisponível')))
    env[0].partners.items[0]['pix_stripe_payouts_enabled'] = True
    with pytest.raises(HTTPException): run(pix.connect_status({'partner_id':'p'}))
    assert env[0].partners.items[0]['pix_stripe_payouts_enabled'] is True


@pytest.mark.parametrize('recipient', ['platform', 'partner', 'influencer'])
@pytest.mark.parametrize('interval', ['manual', None])
def test_bank_automation_required_before_charging(env, recipient, interval):
    client = pix.stripe_client().v1
    if recipient == 'platform':
        account = client.accounts.retrieve_current.return_value
    else:
        from copy import deepcopy
        accounts = {'acct': deepcopy(client.accounts.retrieve.return_value),
                    'acct_inf': deepcopy(client.accounts.retrieve.return_value)}
        account = accounts['acct' if recipient == 'partner' else 'acct_inf']
        client.accounts.retrieve.side_effect = lambda identifier, **kw: accounts[identifier]
    account['settings']['payouts']['schedule']['interval'] = interval
    with pytest.raises(HTTPException):
        run(pix.partner_checkout(body(), {'partner_id': 'p'}))
    env[1].assert_not_called()
    assert not env[0].payment_transactions.items


def test_platform_bank_payouts_disabled_blocks_new_charges(env):
    pix.stripe_client().v1.accounts.retrieve_current.return_value['payouts_enabled'] = False
    with pytest.raises(HTTPException):
        run(pix.partner_checkout(body(), {'partner_id': 'p'}))
    env[1].assert_not_called()


def test_paid_customer_stays_confirmed_when_second_transfer_times_out(env):
    db, _, _ = env
    run(pix.partner_checkout(body(), {'partner_id': 'p'}))
    client = pix.stripe_client().v1
    client.checkout.sessions.retrieve.return_value = paid()
    client.transfers.create.side_effect = [{'id': 'tr_partner'}, pix.stripe.error.APIConnectionError('timeout')]
    first = run(pix.status(db.payment_transactions.items[0]['request_id']))
    assert first['payment_status'] == 'paid' and first['split_status'] == 'pending'
    assert first['partner_transfer_id'] == 'tr_partner'
    client.transfers.create.side_effect = None
    client.transfers.create.return_value = {'id': 'tr_influencer'}
    second = run(pix.status(first['request_id']))
    assert second['payment_status'] == 'paid' and second['split_status'] == 'completed'
    assert client.transfers.create.call_count == 3
    assert len(db.redemptions.items) == 1
    assert env[1].call_count == 1


def test_unconfirmed_customer_is_not_marked_paid_on_provider_outage(env):
    run(pix.partner_checkout(body(), {'partner_id': 'p'}))
    pix.stripe_client().v1.checkout.sessions.retrieve.side_effect = pix.stripe.error.APIConnectionError('timeout')
    with pytest.raises(HTTPException) as error:
        run(pix.status(env[0].payment_transactions.items[0]['request_id']))
    assert error.value.status_code == 502
    assert env[0].payment_transactions.items[0]['payment_status'] == 'pending'
