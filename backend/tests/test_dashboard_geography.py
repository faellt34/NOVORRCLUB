"""Read-only map aggregation; no real database, payments or customer tracking."""
import asyncio
import os
import pytest
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:1')
os.environ.setdefault('DB_NAME', 'offline')
import routes_data


@pytest.mark.parametrize('currency,city', [('eur', 'Lisboa'), ('brl', 'João Pessoa')])
def test_geography_scopes_currency_and_handles_refunds(monkeypatch, currency, city):
    async def scenario():
        db = AsyncMongoMockClient().test
        monkeypatch.setattr(routes_data, 'db', db)
        await db.partners.insert_many([{'id':'pt', 'cidade':'Lisboa', 'status':'Ativo'}, {'id':'br', 'cidade':'João Pessoa', 'currency':'brl', 'status':'Ativo'}])
        for pid, cur in [('pt', 'eur'), ('br', 'brl')]:
            await db.coupon_claims.insert_one({'partner_id':pid, 'currency':cur})
            await db.redemptions.insert_many([{'partner_id':pid, 'currency':cur, 'amount':100}, {'partner_id':pid, 'currency':cur, 'amount':-25, 'is_refund':True}])
        result = await routes_data.admin_geography({'role':'admin'}, currency)
        assert result['currency'] == currency
        assert len(result['cities']) == 1
        row = result['cities'][0]
        assert row['name'] == city and row['revenue'] == 75
        assert row['sales'] == 1 and row['clicks'] == 1 and row['partners'] == 1
        assert 'customer' not in row and 'ip' not in row
    asyncio.run(scenario())


def test_unknown_city_has_no_invented_coordinates(monkeypatch):
    async def scenario():
        db = AsyncMongoMockClient().test
        monkeypatch.setattr(routes_data, 'db', db)
        await db.partners.insert_one({'id':'p', 'cidade':'Desconhecida', 'status':'Ativo'})
        result = await routes_data.admin_geography({'role':'admin'}, 'eur')
        assert result['cities'][0]['lat'] is None
        assert result['cities'][0]['lon'] is None
    asyncio.run(scenario())
