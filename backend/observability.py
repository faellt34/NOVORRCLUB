import logging
import time
import traceback
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core import db, new_id, now_iso

SKIP = ("/api/ws", "/api/realtime", "/api/diretor/logs", "/api/diretor/briefing")
log = logging.getLogger("rrclub")


def _level(status: int) -> str:
    # Validation/onboarding 4xx are normal client/business states, not outages.
    return "error" if status >= 500 else "info"


def _expected_user_state(status: int, path: str) -> bool:
    """Routine P5/Connect validation is not a platform incident.

    Keep request_metrics intact, and keep 5xx plus slow requests visible.
    """
    return status in (409, 422) and (
        path.startswith(("/api/p5/", "/api/partner/"))
        or path.startswith("/api/admin/finance/pt-split/")
    )


async def record(level: str, origem: str, mensagem: str, **extra):
    doc = {"id": new_id("log"), "nivel": level, "origem": origem, "mensagem": mensagem[:2000], "timestamp": now_iso(), "ts": datetime.now(timezone.utc), **extra}
    try:
        await db.system_logs.insert_one(doc)
    except Exception as e:
        log.warning(f"system_logs insert failed: {e}")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api") or path.startswith(SKIP):
            return await call_next(request)
        t0 = time.perf_counter()
        try:
            resp = await call_next(request)
        except Exception as e:
            ms = round((time.perf_counter() - t0) * 1000)
            await record("error", "http", f"{request.method} {path} → 500 {type(e).__name__}: {e}", metodo=request.method, caminho=path, status=500, duracao_ms=ms, traceback=traceback.format_exc()[-3000:])
            log.exception(f"Unhandled error on {request.method} {path}")
            return JSONResponse({"detail": "Erro interno"}, status_code=500)
        ms = round((time.perf_counter() - t0) * 1000)
        lvl = _level(resp.status_code)
        if (lvl != "info" and not _expected_user_state(resp.status_code, path)) or ms > 1500:
            # Preserve 5xx and slow requests; do not fill the incident log with
            # expected KYC, expired QR or invalid user input states.
            await record(lvl if lvl != "info" else "warn", "http",
                         f"{request.method} {path} → {resp.status_code}" + (f" · lento {ms}ms" if ms > 1500 else ""),
                         metodo=request.method, caminho=path, status=resp.status_code, duracao_ms=ms)
        try:
            await db.request_metrics.insert_one({"id": new_id("rm"), "metodo": request.method, "caminho": path, "status": resp.status_code, "duracao_ms": ms, "timestamp": now_iso(), "ts": datetime.now(timezone.utc)})
        except Exception:
            pass
        return resp


async def ensure_indexes():
    await db.system_logs.create_index("ts", expireAfterSeconds=14 * 86400)
    await db.request_metrics.create_index("ts", expireAfterSeconds=7 * 86400)
