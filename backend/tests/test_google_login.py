"""Offline identity tests: never contact Google, production DB or payment APIs."""
import asyncio
import hashlib
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException, Request, Response
from mongomock_motor import AsyncMongoMockClient
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "offline")
os.environ.setdefault("JWT_SECRET", "offline-test-only-secret-never-deploy")
import routes_auth as auth
import google_identity


def request(nonce="challenge"):
    return Request({"type": "http", "method": "POST", "path": "/api/auth/google", "headers": [(b"cookie", f"google_nonce={nonce}".encode())], "client": ("127.0.0.1", 1)})


def setup(monkeypatch, claims=None):
    db = AsyncMongoMockClient(tz_aware=True).test
    monkeypatch.setattr(auth, "db", db)
    monkeypatch.setattr(auth, "rate_limit", AsyncMock())
    monkeypatch.setattr(auth, "audit", AsyncMock())
    monkeypatch.setattr(google_identity, "verify_google_credential", AsyncMock(return_value=claims or {"sub": "g1", "email": "creator@example.test"}))
    return db


async def challenge(db, expired=False):
    await db.google_challenges.insert_one({"digest": hashlib.sha256(b"challenge").hexdigest(), "expires_at": datetime.now(timezone.utc) + timedelta(minutes=-1 if expired else 10)})


def test_challenge_is_consumed_once_and_cannot_be_replayed(monkeypatch):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db)
        await auth.google_claims(auth.GoogleIn(credential="fake"), request())
        with pytest.raises(HTTPException) as e:
            await auth.google_claims(auth.GoogleIn(credential="fake"), request())
        assert e.value.status_code == 401
    asyncio.run(scenario())


def test_expired_challenge_is_rejected(monkeypatch):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db, True)
        with pytest.raises(HTTPException) as e:
            await auth.google_claims(auth.GoogleIn(credential="fake"), request())
        assert e.value.status_code == 401
    asyncio.run(scenario())


@pytest.mark.parametrize("status", ["Pendente", "Suspenso"])
def test_google_cannot_bypass_account_approval_or_suspension(monkeypatch, status):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db)
        await db.users.insert_one({"id":"u", "google_sub":"g1", "status":status})
        response = Response()
        with pytest.raises(HTTPException) as e:
            await auth.google_login(auth.GoogleIn(credential="fake"), request(), response)
        assert e.value.status_code == 403
        assert "set-cookie" not in response.headers
    asyncio.run(scenario())


def test_matching_email_does_not_silently_take_over_password_account(monkeypatch):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db)
        await db.users.insert_one({"id":"u", "email":"creator@example.test", "role":"admin"})
        with pytest.raises(HTTPException) as e:
            await auth.google_login(auth.GoogleIn(credential="fake"), request(), Response())
        assert e.value.status_code == 409
        assert "google_sub" not in await db.users.find_one({"id":"u"})
    asyncio.run(scenario())


def test_link_requires_matching_email(monkeypatch):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db)
        with pytest.raises(HTTPException) as e:
            await auth.google_link(auth.GoogleIn(credential="fake"), request(), {"id":"u", "email":"other@example.test"})
        assert e.value.status_code == 400
    asyncio.run(scenario())


def test_google_registration_preserves_country_and_pending_partner(monkeypatch):
    async def scenario():
        db = setup(monkeypatch)
        await challenge(db)
        monkeypatch.setattr(auth, "notify", AsyncMock())
        monkeypatch.setattr(auth, "admin_ids", AsyncMock(return_value=[]))
        response = Response()
        result = await auth.google_login(auth.GoogleIn(credential="fake", role="partner", aceita_termos=True, currency="brl", cidade="João Pessoa", nome="Espaço"), request(), response)
        assert result["pending"] is True and "token" not in result
        user = await db.users.find_one({"google_sub":"g1"})
        assert user["status"] == "Pendente" and user["currency"] == "brl"
        assert (await db.partners.find_one({"user_id":user["id"]}))["currency"] == "brl"
        assert "set-cookie" not in response.headers
    asyncio.run(scenario())


@pytest.mark.parametrize("changes", [{"nonce":"wrong"}, {"email_verified":False}, {"iss":"https://attacker.test"}, {"sub":""}])
def test_invalid_google_claims_are_rejected(monkeypatch, changes):
    from google.oauth2 import id_token
    claims = {"sub":"g1", "email":"creator@example.test", "email_verified":True, "nonce":"challenge", "iss":"https://accounts.google.com", **changes}
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "offline-client-id")
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda credential, transport, audience: claims)
    with pytest.raises(HTTPException) as e:
        asyncio.run(google_identity.verify_google_credential("fake", "challenge"))
    assert e.value.status_code == 401


def test_google_verifier_receives_our_client_id_as_audience(monkeypatch):
    from google.oauth2 import id_token
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "offline-client-id")
    def verify(credential, transport, audience):
        assert audience == "offline-client-id"
        return {"sub":"g1", "email":"creator@example.test", "email_verified":True, "nonce":"challenge", "iss":"https://accounts.google.com"}
    monkeypatch.setattr(id_token, "verify_oauth2_token", verify)
    assert asyncio.run(google_identity.verify_google_credential("fake", "challenge"))["sub"] == "g1"
