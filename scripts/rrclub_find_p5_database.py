#!/usr/bin/env python3
"""Locate one exact coupon in accessible app databases. Read-only; no secrets printed."""
from pathlib import Path
import os
import subprocess
import sys


def bootstrap():
    candidates = ['/root/.venv/bin/python', '/app/.venv/bin/python', '/opt/venv/bin/python', sys.executable]
    for proc in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = proc.read_bytes().decode().split('\0')
            if not any('uvicorn' in arg for arg in args):
                continue
            first = Path(args[0])
            if 'python' in first.name:
                candidates.insert(0, str(first))
            elif first.is_file():
                line = first.read_text().splitlines()[0]
                if line.startswith('#!/') and 'python' in line:
                    candidates.insert(0, line[2:])
        except Exception:
            pass
    for python in dict.fromkeys(candidates):
        if not Path(python).is_file():
            continue
        test = subprocess.run([python, '-c', 'import dotenv,motor'], capture_output=True)
        if test.returncode == 0:
            env = dict(os.environ, RRCLUB_DB_DIAG_CHILD='1')
            return subprocess.run([python, __file__], env=env).returncode
    print('Python do backend não localizado. Nenhuma alteração efetuada.')
    return 1


async def diagnose():
    import json
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    load_dotenv('/app/backend/.env', override=False)
    code = 'SHEYSO-7182'
    uri = os.environ.get('MONGO_URL')
    if not uri:
        print('MONGO_URL ausente. Nenhuma alteração efetuada.')
        return
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)
    report = {'coupon': code, 'read_only': True, 'configured_database': os.environ.get('DB_NAME'), 'matches': []}
    try:
        try:
            names = await client.list_database_names()
        except Exception:
            report['reason'] = 'database_listing_not_permitted'
            names = [os.environ.get('DB_NAME')]
        for name in names[:100]:
            if not name or name in ('admin', 'local', 'config'):
                continue
            database = client[name]
            try:
                campaign = await database.campaigns.find_one({'cupom': code},
                    {'_id': 0, 'id': 1, 'cupom': 1, 'parceiro_id': 1, 'influencer_id': 1, 'currency': 1})
                if not campaign:
                    continue
                match = {'database': name, 'campaign': campaign, 'recipients': []}
                for role, collection, field in (
                    ('partner', database.partners, 'parceiro_id'),
                    ('influencer', database.influencers, 'influencer_id'),
                ):
                    entity = await collection.find_one({'id': campaign.get(field)},
                        {'_id': 0, 'id': 1, 'pix_stripe_account_id': 1, 'currency': 1})
                    match['recipients'].append({'role': role, 'record': entity})
                report['matches'].append(match)
            except Exception:
                continue
        if not report['matches']:
            report['reason'] = report.get('reason') or 'coupon_not_in_accessible_databases'
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    if os.environ.get('RRCLUB_DB_DIAG_CHILD') != '1':
        sys.exit(bootstrap())
    import asyncio
    try:
        asyncio.run(diagnose())
    except Exception as error:
        print('Consulta não concluída:', type(error).__name__)
