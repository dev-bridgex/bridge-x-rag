from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.db.mongodb import get_db

async def get_database() -> AsyncIOMotorDatabase:
    db = await get_db()
    return db 