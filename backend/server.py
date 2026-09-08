from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

import logging
import os

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from core import client
from seed import seed
import routes_auth, routes_data, routes_admin, routes_leads, routes_messages

app = FastAPI(title="Robson Club API")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Robson Club API", "status": "ok"}


for r in (routes_auth.router, routes_data.router, routes_admin.router, routes_leads.router, routes_messages.router):
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
