import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('DB_NAME', 'rrclub_test')
import routes_ai as ai


def test_ai_budget_error_is_actionable_without_leaking_provider_details():
    error = ai.ai_error_message(RuntimeError('Budget has been exceeded private upstream secret'))
    assert 'orçamento' in error
    assert 'secret' not in error
    assert 'secret' not in ai.ai_error_message(RuntimeError('private secret'))


def test_missing_ai_configuration_returns_503_without_provider_call(monkeypatch):
    monkeypatch.delenv('EMERGENT_LLM_KEY', raising=False)
    with pytest.raises(HTTPException) as error:
        asyncio.run(ai.ai_ask(ai.AskIn(message='Resumo'), {'id': 'admin'}, 'brl'))
    assert error.value.status_code == 503


def test_ai_context_filters_currency_and_refunds(monkeypatch):
    class Collection:
        def __init__(self, records): self.records = records; self.query = None
        def find(self, query, projection): self.query = query; return self
        async def to_list(self, limit): return self.records
        async def count_documents(self, query): return 0
    reds = Collection([{'coupon': 'BR', 'amount': 100, 'commission': 5}, {'coupon': 'BR', 'amount': -50, 'commission': -2.5, 'is_refund': True}])
    database = SimpleNamespace(redemptions=reds, coupon_claims=Collection([]), campaigns=Collection([]), influencers=Collection([]), partners=Collection([]))
    monkeypatch.setattr(ai, 'db', database)
    result = json.loads(asyncio.run(ai._context('brl')))
    assert result['moeda'] == 'BRL'
    assert result['totais']['vendas'] == 1
    assert result['totais']['receita'] == 50
    assert result['totais']['comissoes'] == 2.5
    assert reds.query['$and'][1] == {'currency': 'brl'}
