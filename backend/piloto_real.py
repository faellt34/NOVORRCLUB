"""Marco único, não destrutivo, do piloto real RRClub.

Nunca elimina eventos, campanhas ou lançamentos financeiros: apenas define
o início da janela usada nos indicadores operacionais verificados.
"""
from datetime import datetime, timedelta, timezone

PILOT_KEY = "rrclub_piloto_real_v1"


def effective_cutoff(days=30, pilot_since=None, *, now=None):
    """Devolve a data mais recente entre a janela pedida e o início do piloto."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("O relógio deve incluir o fuso horário")
    cutoff = now.astimezone(timezone.utc) - timedelta(days=max(1, min(int(days), 90)))
    if pilot_since:
        start = datetime.fromisoformat(pilot_since.replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError("O marco do piloto deve incluir o fuso horário")
        cutoff = max(cutoff, start.astimezone(timezone.utc))
    return cutoff.isoformat()


async def read_pilot_since():
    from core import db

    record = await db.platform_settings.find_one({"_id": PILOT_KEY}, {"started_at": 1})
    return record.get("started_at") if record else None


async def start_pilot_once(admin_id):
    """Idempotente, até com dois administradores em simultâneo."""
    from core import db, now_iso
    from pymongo.errors import DuplicateKeyError

    try:
        await db.platform_settings.update_one(
            {"_id": PILOT_KEY},
            {"$setOnInsert": {"started_at": now_iso(), "started_by": admin_id}},
            upsert=True,
        )
    except DuplicateKeyError:
        # Uma chamada simultânea já fixou o início; não substituímos o marco.
        pass
    return await read_pilot_since()
