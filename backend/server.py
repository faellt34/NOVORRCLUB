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
import routes_auth, routes_data, routes_admin, routes_leads, routes_messages, routes_payments, routes_ops
from routes_payments import ensure_tax_settings, ensure_price, SUBSCRIPTION
from storage import init_storage

app = FastAPI(title="Robson Club API")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Robson Club API", "status": "ok"}


for r in (routes_auth.router, routes_ops.router, routes_payments.router, routes_data.router, routes_leads.router, routes_messages.router, routes_admin.router):
    api_router.include_router(r)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.on_event("startup")
async def on_startup():
    await seed()
    await db.entitlements.create_index([("user_id", 1), ("ebook_id", 1)], unique=True)
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.payouts.create_index([("influencer_id", 1), ("month", 1)], unique=True)
    try:
        init_storage()
    except Exception as e:
        logging.getLogger(__name__).error(f"Storage init failed: {e}")
    try:
        await asyncio.to_thread(ensure_tax_settings)
        await asyncio.to_thread(ensure_price, SUBSCRIPTION["lookup_key"], SUBSCRIPTION["name"], SUBSCRIPTION["amount"], SUBSCRIPTION["emergent_product_id"], SUBSCRIPTION["interval"])
    except Exception as e:
        logging.getLogger(__name__).error(f"Stripe catalog init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
