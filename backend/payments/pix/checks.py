"""Read-only checks for the existing BR separate-charges-and-transfers flow.

Pix availability on a Portuguese merchant account does not certify that account
for the Brazilian recipients/split configured by this application.
"""
from fastapi import HTTPException

WEBHOOK_EVENTS = frozenset({
    'checkout.session.completed', 'checkout.session.async_payment_succeeded',
    'checkout.session.async_payment_failed', 'checkout.session.expired',
    'charge.refunded', 'charge.dispute.created', 'charge.dispute.updated',
    'charge.dispute.closed',
})


def payout_schedule(account):
    """Accounts v1 is deliberately retained for the existing Stripe SDK.

    Brazil uses automatic daily payouts. Missing settings mean unverified,
    never proof that money will automatically reach the bank.
    """
    return (((account.get('settings') or {}).get('payouts') or {}).get('schedule') or {}).get('interval')


def platform_checks(account):
    return {
        'platform_country_br': account.get('country') == 'BR',
        'platform_currency_brl': account.get('default_currency') == 'brl',
        'platform_charges_enabled': account.get('charges_enabled') is True,
        'platform_payouts_enabled': account.get('payouts_enabled') is True,
        'platform_automatic_payouts': payout_schedule(account) == 'daily',
        'platform_pix_active': (account.get('capabilities') or {}).get('pix_payments') == 'active',
    }


def configuration_checks(configuration):
    enabled = sorted(k for k, value in configuration.items()
                     if isinstance(value, dict) and value.get('available') is True
                     and (value.get('display_preference') or {}).get('value') == 'on')
    return {
        'configuration_active': configuration.get('active') is True,
        'configuration_pix_only': enabled == ['pix'],
    }


def receiving_status(account, entity):
    metadata = account.get('metadata') or {}
    # A blank metadata dict is NOT proof of ownership. Never route funds to an
    # unverified account, even if the bank/email seems to belong to the owner.
    if not metadata.get('partner_id') or metadata['partner_id'] != entity['id']:
        raise HTTPException(409, 'Titularidade Connect não comprovada para este cadastro; conclua ou reconcilie o onboarding.')
    if account.get('country') != 'BR':
        raise HTTPException(409, 'A conta de recebimento deste fluxo deve estar domiciliada no Brasil.')
    transfers = (account.get('capabilities') or {}).get('transfers') == 'active'
    interval = payout_schedule(account)
    return {
        'connected': True, 'status_verified': True, 'country': 'BR',
        'charges_enabled': bool(account.get('charges_enabled')),
        'payouts_enabled': bool(account.get('payouts_enabled')),
        'transfers_enabled': transfers,
        'automatic_payouts': interval == 'daily',
        'payout_interval': interval,
        'receiving_ready': transfers and bool(account.get('payouts_enabled')) and interval == 'daily',
        'details_submitted': bool(account.get('details_submitted')),
    }


def webhook_checks(endpoints, origin):
    expected = origin.rstrip('/') + '/api/stripe/pix/webhook'
    for endpoint in endpoints:
        if endpoint.get('url') != expected or endpoint.get('status') != 'enabled':
            continue
        enabled = set(endpoint.get('enabled_events') or [])
        if '*' in enabled or WEBHOOK_EVENTS.issubset(enabled):
            return True
    return False
