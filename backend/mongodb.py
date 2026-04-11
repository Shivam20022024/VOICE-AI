# mongodb.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# Load env values for local runs (supports both backend/.env.local and project .env.local).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env.local"))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env.local"))

MONGO_URI = os.environ.get("MONGODB_URI")  # e.g. mongodb+srv://user:pass@cluster.mongodb.net/mydb?retryWrites=true&w=majority
MONGO_DB_NAME = os.environ.get("MONGODB_DB", "voiceai")

if not MONGO_URI:
    raise RuntimeError("Please set the MONGODB_URI environment variable.")

_client: Optional[AsyncIOMotorClient] = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client

def get_db():
    client = get_client()
    return client[MONGO_DB_NAME]

async def ensure_indexes():
    """
    Create required indexes on first startup.
    """
    db = get_db()
    calls = db.calls
    # Ensure unique index on call_id for upsert behaviour
    await calls.create_index("call_id", unique=True)
    # Index by created_at for fast sorting
    await calls.create_index([("created_at", -1)])
async def ensure_indexes():
    db = get_db()

    # ✅ WEEKLY AUTO DELETE
    await db.calls.create_index(
        "expiresAt",
        expireAfterSeconds=0
    )
