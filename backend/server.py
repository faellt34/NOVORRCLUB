from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

import asyncio
import logging
import os

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from core import client, db
from seed import seed
from clone_guard import require_isolated_clone
import routes_pix
import routes_mbway_sandbox
import routes_auth, routes_data, routes_admin, routes_leads, routes_messages, routes_payments, routes_ops, realtime, routes_test, routes_ai, routes_diretor
from routes_payments import ensure_tax_settings, ensure_price, SUBSCRIPTION
from storage import init_storage
from observability import RequestLogMiddleware, ensure_indexes as ensure_log_indexes

app = FastAPI(title="Robson Club API")
app.add_middleware(RequestLogMiddleware)
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Robson Club API", "status": "ok"}


for r in (routes_pix.router, routes_mbway_sandbox.router, routes_auth.router, routes_ops.router, routes_test.router, routes_ai.router, routes_diretor.router, routes_payments.router, routes_data.router, routes_leads.router, routes_messages.router, routes_admin.router, realtime.router):
    api_router.include_router(r)

app.include_router(api_router)

_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_credentials="*" not in _origins,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.on_event("startup")
async def on_startup():
    # Never initialize schemas, users or catalogs against a production environment.
    require_isolated_clone()
    await db.users.create_index("google_sub", unique=True, partialFilterExpression={"google_sub": {"$type": "string"}})
    await db.google_challenges.create_index("expires_at", expireAfterSeconds=0)
    await seed()
    await db.entitlements.create_index([("user_id", 1), ("ebook_id", 1)], unique=True)
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.password_reset_tokens.create_index("token", unique=True)
    # Migrate legacy payout keys without deleting financial records.
    await db.payouts.update_many({"currency": {"$exists": False}}, {"$set": {"currency": "eur"}})
    await db.payouts.create_index([("influencer_id", 1), ("month", 1), ("currency", 1)], unique=True)
    payout_indexes = await db.payouts.index_information()
    for index_name, index in payout_indexes.items():
        if list(index.get("key", [])) == [("influencer_id", 1), ("month", 1)]:
            await db.payouts.drop_index(index_name)
    await ensure_log_indexes()
    # No automatic Stripe Tax modification: an incorrect legal address or
    # tax setting could affect live accounting. No automatic catalog writes.
    # Storage also remains disabled until the isolated deployment is configured.
    if os.getenv("RRCLUB_CLONE_STORAGE_ENABLED", "").lower() == "true":
        try:
            init_storage()
        except Exception:
            logging.getLogger(__name__).exception("Clone storage initialization failed")



@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
