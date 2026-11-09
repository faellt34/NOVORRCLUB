"""Profile, account ownership and password tests; no live storage or database."""
import asyncio
import io
import os
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from mongomock_motor import AsyncMongoMockClient
from PIL import Image

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "rrclub_offline_profile")
import routes_profile as profile
import routes_admin as admin


def run(coro):
    return asyncio.run(coro)


def picture(fmt="PNG"):
    output = io.BytesIO()
    Image.new("RGB", (1000, 800), "navy").save(output, format=fmt)
    return output.getvalue()


def upload(raw):
    return UploadFile(filename="image.png", file=io.BytesIO(raw))


@pytest.fixture
def env(monkeypatch):
    db = AsyncMongoMockClient().profiles
    storage = []
    monkeypatch.setattr(profile, "db", db)
    monkeypatch.setattr(profile, "audit", AsyncMock())
    monkeypatch.setattr(profile, "rate_limit", AsyncMock())
    monkeypatch.setattr(profile, "put_object", lambda path, data, ctype: storage.append((path, data, ctype)) or {"ok": True})
    monkeypatch.setattr(profile, "get_object", lambda path: (picture("JPEG"), "image/jpeg"))
    monkeypatch.setenv("FRONTEND_URL", "https://rrclub.online")
    return db, storage


def test_partner_avatar_keeps_existing_financial_fields(env):
    db, storage = env
    user = {"id": "u-1", "role": "partner", "partner_id": "partner-1", "nome": "Loja"}
    async def scenario():
        await db.users.insert_one({**user, "avatar": "old"})
        await db.partners.insert_one({
            "id": "partner-1", "user_id": "u-1", "avatar": "old", "currency": "brl",
            "pix_stripe_account_id": "acct_preserved", "status": "Ativo",
        })
        result = await profile.update_avatar(file=upload(picture()), user=user)
        merchant = await db.partners.find_one({"id": "partner-1"})
        account = await db.users.find_one({"id": "u-1"})
        assert merchant["avatar"] == account["avatar"] == result["avatar"]
        assert merchant["pix_stripe_account_id"] == "acct_preserved"
        assert merchant["currency"] == "brl"
        assert merchant["status"] == "Ativo"
        assert len(storage) == 1 and storage[0][2] == "image/jpeg"
        assert result["avatar"].startswith("https://rrclub.online/api/public/avatars/partner/")
    run(scenario())


def test_influencer_avatar_updates_only_own_profile(env):
    db, storage = env
    user = {"id": "u-2", "role": "influencer", "influencer_id": "inf-1"}
    async def scenario():
        await db.users.insert_one({**user, "avatar": "before"})
        await db.influencers.insert_one({"id": "inf-1", "user_id": "u-2", "avatar": "before"})
        await db.influencers.insert_one({"id": "inf-2", "user_id": "u-other", "avatar": "untouched"})
        updated = await profile.update_avatar(file=upload(picture()), user=user)
        assert (await db.influencers.find_one({"id": "inf-1"}))["avatar"] == updated["avatar"]
        assert (await db.influencers.find_one({"id": "inf-2"}))["avatar"] == "untouched"
    run(scenario())


def test_cross_account_upload_rejected_without_storage_write(env):
    db, storage = env
    async def scenario():
        await db.partners.insert_one({"id": "partner-1", "user_id": "other", "avatar": "old"})
        with pytest.raises(HTTPException) as exc:
            await profile.update_avatar(file=upload(picture()), user={
                "id": "attacker", "role": "partner", "partner_id": "partner-1",
            })
        assert exc.value.status_code == 409
        assert not storage
        assert (await db.partners.find_one({"id": "partner-1"}))["avatar"] == "old"
    run(scenario())


def test_broken_upload_has_no_storage_write(env):
    _, storage = env
    with pytest.raises(HTTPException) as exc:
        run(profile.update_avatar(file=upload(b"invalid"), user={
            "id": "u-1", "role": "partner", "partner_id": "partner-1",
        }))
    assert exc.value.status_code == 415 and not storage


def test_storage_outage_does_not_change_avatar(env, monkeypatch):
    db, _ = env
    def fail(*args):
        raise RuntimeError("storage offline")
    monkeypatch.setattr(profile, "put_object", fail)
    async def scenario():
        await db.partners.insert_one({"id": "partner-1", "user_id": "u-1", "avatar": "old"})
        with pytest.raises(HTTPException) as exc:
            await profile.update_avatar(file=upload(picture()), user={
                "id": "u-1", "role": "partner", "partner_id": "partner-1",
            })
        assert exc.value.status_code == 503
        assert (await db.partners.find_one({"id": "partner-1"}))["avatar"] == "old"
    run(scenario())


def test_cover_is_separate_and_preserves_avatar(env):
    db, storage = env
    async def scenario():
        await db.users.insert_one({"id": "u-1", "role": "partner", "partner_id": "partner-1", "avatar": "existing"})
        await db.partners.insert_one({"id": "partner-1", "user_id": "u-1", "avatar": "existing", "pix_stripe_account_id": "acct_abc"})
        value = await profile.update_cover(file=upload(picture()), user={"id": "u-1", "role": "partner", "partner_id": "partner-1"})
        merchant = await db.partners.find_one({"id": "partner-1"})
        assert merchant["cover_image"] == value["cover_image"]
        assert merchant["avatar"] == "existing"
        assert merchant["pix_stripe_account_id"] == "acct_abc"
        assert len(storage) == 1
        with Image.open(io.BytesIO(storage[0][1])) as converted:
            assert converted.size == (1200, 675)
    run(scenario())


def test_public_image_is_jpeg_and_invalid_path_is_rejected(env):
    data = run(profile.public_avatar("partner", "partner-1", "0123456789abcdef0123456789abcdef"))
    assert data.media_type == "image/jpeg"
    assert data.headers["x-content-type-options"] == "nosniff"
    with pytest.raises(HTTPException) as exc:
        run(profile.public_avatar("partner", "../outside", "0123456789abcdef0123456789abcdef"))
    assert exc.value.status_code == 404


def test_admin_user_creation_requires_explicit_password():
    with pytest.raises(HTTPException) as missing:
        run(admin.prepare("usuarios", {"email": "new@example.test", "nome": "Novo", "papel": "Parceiro"}, True))
    assert missing.value.status_code == 422
    with pytest.raises(HTTPException) as weak:
        run(admin.prepare("usuarios", {"email": "new@example.test", "nome": "Novo", "password": "123", "papel": "Parceiro"}, True))
    assert weak.value.status_code == 422
    result = run(admin.prepare("usuarios", {"email": "new@example.test", "nome": "Novo", "password": "ValidPassword123", "papel": "Parceiro"}, True))
    assert result["password_hash"] and "password" not in result


def test_admin_edit_without_password_keeps_existing_hash():
    result = run(admin.prepare("usuarios", {"nome": "Renomeado", "papel": "Parceiro"}, False))
    assert "password_hash" not in result
    with pytest.raises(HTTPException) as invalid:
        run(admin.prepare("usuarios", {"nome": "Renomeado", "password": "weak"}, False))
    assert invalid.value.status_code == 422
