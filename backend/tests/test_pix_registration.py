"""Registration must work before the Brazilian Stripe account exists."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import Response
from pydantic import ValidationError
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "rrclub_test")
os.environ.setdefault("JWT_SECRET", "test-only-key-with-at-least-32-characters")
import routes_auth as auth

@pytest.mark.parametrize("role,currency,pending", [
    ("partner", "brl", True), ("influencer", "brl", False), ("influencer", "eur", False),
])
def test_registration_without_stripe_credentials(monkeypatch, role, currency, pending):
    monkeypatch.delenv("PIX_STRIPE_SECRET_KEY", raising=False)
    collections = {name: SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock())
                   for name in ("users", "partners", "influencers")}
    monkeypatch.setattr(auth, "db", SimpleNamespace(**collections))
    monkeypatch.setattr(auth, "audit", AsyncMock())
    monkeypatch.setattr(auth, "notify", AsyncMock())
    monkeypatch.setattr(auth, "admin_ids", AsyncMock(return_value=[]))
    body = auth.RegisterIn(nome="Teste Brasil", email="teste@example.com", password="test-password",
                           role=role, currency=currency, aceita_termos=True)
    result = asyncio.run(auth.register(body, Response()))
    assert result["pending"] is pending
    assert result["user"]["currency"] == currency
    entity = collections["partners" if role == "partner" else "influencers"].insert_one.call_args.args[0]
    assert entity["currency"] == currency
    assert entity["status"] == ("Pendente" if pending else "Ativo")
    assert "pix_stripe_account_id" not in entity

def test_currency_defaults_to_portugal_and_rejects_unknown_values():
    fields = dict(nome="Teste", email="test@example.com", password="password", role="influencer")
    assert auth.RegisterIn(**fields).currency == "eur"
    with pytest.raises(ValidationError):
        auth.RegisterIn(**fields, currency="usd")
