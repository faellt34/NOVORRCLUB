"""Fotografias de perfil RRClub (parceiro/influenciador).

Usa armazenamento existente; não altera Stripe, cupões nem contas.
A imagem publicada é intencionalmente pública e não contém dados pessoais internos.
"""
import asyncio
import io
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError

from core import db, NO_ID, audit, now_iso, require_role, rate_limit
from storage import get_object, put_object

router = APIRouter()
MAX_UPLOAD = 3 * 1024 * 1024
MAX_PIXELS = 16_000_000
ENTITY_ID = re.compile(r"^[A-Za-z0-9_-]{2,80}$")
PHOTO_ID = re.compile(r"^[a-f0-9]{32}$")


def prepare_photo(data: bytes, cover: bool = False) -> bytes:
    if not data or len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Fotografia demasiado grande (máximo 3 MB)")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("JPEG", "PNG", "WEBP"):
                raise HTTPException(415, "Utilize JPG, PNG ou WebP")
            if source.width * source.height > MAX_PIXELS:
                raise HTTPException(413, "Dimensões da imagem demasiado grandes")
            source.load()
            photo = ImageOps.exif_transpose(source).convert("RGB")
            if cover:
                photo = ImageOps.fit(photo, (1200, 675), Image.Resampling.LANCZOS)
            else:
                photo.thumbnail((640, 640), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            photo.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(415, "Ficheiro de imagem inválido") from exc


@router.post("/profile/avatar")
async def update_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(require_role("partner", "influencer")),
):
    """Só o titular autenticado pode atualizar a sua própria fotografia."""
    await rate_limit("avatar:" + user["id"], 8, 3600)
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    image = await asyncio.to_thread(prepare_photo, data)

    role = user["role"]
    collection = db.partners if role == "partner" else db.influencers
    id_key = "partner_id" if role == "partner" else "influencer_id"
    entity_id = user.get(id_key)
    if not entity_id or not ENTITY_ID.fullmatch(entity_id):
        raise HTTPException(409, "Conta comercial não associada; peça verificação ao administrador")
    entity = await collection.find_one({"id": entity_id, "user_id": user["id"]}, NO_ID)
    if not entity:
        raise HTTPException(409, "Associação do perfil não confirmada")

    photo_id = uuid.uuid4().hex
    path = f"avatars/{role}/{entity_id}/{photo_id}.jpg"
    origin = (os.environ.get("FRONTEND_URL") or "").rstrip("/")
    if not origin.startswith("https://"):
        raise HTTPException(503, "Domínio público da RRClub não configurado")
    url = f"{origin}/api/public/avatars/{role}/{entity_id}/{photo_id}.jpg"

    try:
        await asyncio.to_thread(put_object, path, image, "image/jpeg")
    except Exception as exc:
        raise HTTPException(503, "Não foi possível guardar a fotografia") from exc

    old_avatar = entity.get("avatar")
    updated = await collection.update_one(
        {"id": entity_id, "user_id": user["id"], "avatar": old_avatar},
        {"$set": {"avatar": url, "avatar_updated_at": now_iso()}},
    )
    if not updated.matched_count:
        raise HTTPException(409, "O perfil foi atualizado noutro local; tente novamente")
    try:
        saved_user = await db.users.update_one(
            {"id": user["id"], "role": role, id_key: entity_id},
            {"$set": {"avatar": url}},
        )
        if not saved_user.matched_count:
            raise RuntimeError("Utilizador associado não encontrado")
    except Exception as exc:
        await collection.update_one(
            {"id": entity_id, "user_id": user["id"], "avatar": url},
            {"$set": {"avatar": old_avatar}},
        )
        raise HTTPException(503, "Não foi possível sincronizar a fotografia") from exc

    await audit("AVATAR", "Fotografia de perfil atualizada", user, entity_id)
    return {"ok": True, "avatar": url}


@router.get("/public/avatars/{role}/{entity_id}/{photo_id}.jpg")
async def public_avatar(role: str, entity_id: str, photo_id: str):
    """Imagem pública para campanhas e dashboards, sem acesso a caminhos arbitrários."""
    if role not in ("partner", "influencer") or not ENTITY_ID.fullmatch(entity_id) or not PHOTO_ID.fullmatch(photo_id):
        raise HTTPException(404, "Fotografia não encontrada")
    path = f"avatars/{role}/{entity_id}/{photo_id}.jpg"
    try:
        data, _ = await asyncio.to_thread(get_object, path)
    except Exception as exc:
        raise HTTPException(404, "Fotografia não encontrada") from exc
    return Response(content=data, media_type="image/jpeg", headers={
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    })


@router.get("/admin/system/version")
async def release_version(user: dict = Depends(require_role("admin"))):
    """Diagnóstico da versão publicada; nunca assume a branch a partir do domínio."""
    commit = (os.environ.get("RRCLUB_RELEASE_SHA") or os.environ.get("RENDER_GIT_COMMIT")
              or os.environ.get("GITHUB_SHA") or os.environ.get("COMMIT_SHA") or "").strip()
    if not re.fullmatch(r"[a-fA-F0-9]{7,40}", commit):
        commit = None
    return {
        "application": "RRClub",
        "release_sha": commit,
        "release_identified": bool(commit),
        "source": "runtime_environment" if commit else "unavailable",
        "message": ("Identificador informado pelo ambiente; confirme no painel de deploy."
                    if commit else "Versão não identificada; não inferir GitHub = produção."),
    }


@router.post("/profile/cover")
async def update_cover(
    file: UploadFile = File(...),
    user: dict = Depends(require_role("partner")),
):
    """Capa comercial do estabelecimento, separada da fotografia do login."""
    await rate_limit("cover:" + user["id"], 6, 3600)
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    image = await asyncio.to_thread(prepare_photo, data, True)

    partner_id = user.get("partner_id")
    if not partner_id or not ENTITY_ID.fullmatch(partner_id):
        raise HTTPException(409, "Conta comercial não associada")
    entity = await db.partners.find_one({"id": partner_id, "user_id": user["id"]}, NO_ID)
    if not entity:
        raise HTTPException(409, "Associação do estabelecimento não confirmada")
    origin = (os.environ.get("FRONTEND_URL") or "").rstrip("/")
    if not origin.startswith("https://"):
        raise HTTPException(503, "Domínio público da RRClub não configurado")
    photo_id = uuid.uuid4().hex
    path = f"covers/partner/{partner_id}/{photo_id}.jpg"
    url = f"{origin}/api/public/covers/partner/{partner_id}/{photo_id}.jpg"
    try:
        await asyncio.to_thread(put_object, path, image, "image/jpeg")
    except Exception as exc:
        raise HTTPException(503, "Não foi possível guardar a capa") from exc

    old_cover = entity.get("cover_image")
    saved = await db.partners.update_one(
        {"id": partner_id, "user_id": user["id"], "cover_image": old_cover},
        {"$set": {"cover_image": url, "cover_updated_at": now_iso()}},
    )
    if not saved.matched_count:
        raise HTTPException(409, "O estabelecimento foi atualizado noutro local")
    try:
        updated = await db.users.update_one(
            {"id": user["id"], "role": "partner", "partner_id": partner_id},
            {"$set": {"cover_image": url}},
        )
        if not updated.matched_count:
            raise RuntimeError("Utilizador associado não encontrado")
    except Exception as exc:
        await db.partners.update_one(
            {"id": partner_id, "user_id": user["id"], "cover_image": url},
            {"$set": {"cover_image": old_cover}},
        )
        raise HTTPException(503, "Não foi possível sincronizar a capa") from exc
    await audit("CAPA", "Imagem comercial do parceiro atualizada", user, partner_id)
    return {"ok": True, "cover_image": url}


@router.get("/public/covers/partner/{entity_id}/{photo_id}.jpg")
async def public_cover(entity_id: str, photo_id: str):
    if not ENTITY_ID.fullmatch(entity_id) or not PHOTO_ID.fullmatch(photo_id):
        raise HTTPException(404, "Capa não encontrada")
    try:
        data, _ = await asyncio.to_thread(get_object, f"covers/partner/{entity_id}/{photo_id}.jpg")
    except Exception as exc:
        raise HTTPException(404, "Capa não encontrada") from exc
    return Response(content=data, media_type="image/jpeg", headers={
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    })
