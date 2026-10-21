#!/usr/bin/env python3
"""Read-only local campaign diagnostic. No accounts, payments or metadata writes."""
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path('/app') if Path('/app/backend/core.py').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT / 'backend/.env', override=False)
from core import db, client, NO_ID
from routes_pix import provider, provider_readiness
from payments.pix.checks import receiving_status
from fastapi import HTTPException


async def main(code):
    report = {'coupon': code, 'read_only': True}
    try:
        campaign = await db.campaigns.find_one({'cupom': code}, NO_ID)
        if not campaign:
            report['error'] = 'campaign_not_found'
            return report
        report['campaign_id'] = campaign['id']
        report['currency'] = campaign.get('currency')
        report['recipients'] = []
        for role, collection, field in (
            ('partner', db.partners, 'parceiro_id'),
            ('influencer', db.influencers, 'influencer_id'),
        ):
            entity_id = campaign.get(field)
            entity = await collection.find_one({'id': entity_id}, NO_ID) if entity_id else None
            row = {'role': role, 'entity_id': entity_id,
                   'account_id': (entity or {}).get('pix_stripe_account_id')}
            if not entity or not row['account_id']:
                row['reason'] = 'association_missing'
            else:
                try:
                    account = await provider('accounts.retrieve', row['account_id'])
                    row.update(country=account.get('country'),
                               transfers=(account.get('capabilities') or {}).get('transfers'),
                               payouts_enabled=account.get('payouts_enabled'),
                               binding={k: v for k, v in (account.get('metadata') or {}).items()
                                        if k in ('partner_id', 'influencer_id')})
                    row['status'] = receiving_status(account, entity, role)
                except HTTPException as exc:
                    row['reason'] = (exc.headers or {}).get('X-RRClub-Reason', 'recipient_not_ready')
                except Exception:
                    row['reason'] = 'provider_query_failed'
            report['recipients'].append(row)
        try:
            result = await provider_readiness({'role': 'admin'})
            report['platform_checks'] = result.get('checks')
            report['missing_configuration'] = result.get('missing_configuration')
            report['provider_verified'] = result.get('provider_verified')
        except Exception:
            report['platform_check_error'] = 'provider_query_failed'
        latest = await db.p5_charges.find_one({'campaign_id': campaign['id']}, NO_ID,
                                             sort=[('created_at', -1)])
        if latest:
            report['latest_p5'] = {k: latest.get(k) for k in
                                  ('id', 'status', 'financial_state', 'partner_id', 'influencer_id')}
        return report
    finally:
        client.close()


if __name__ == '__main__':
    print(json.dumps(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'SHEYSO-7182')),
                     ensure_ascii=False, indent=2))
