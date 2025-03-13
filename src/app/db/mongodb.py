import os 
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from app.helpers.config import get_settings
from fastapi import HTTPException


app_settings = get_settings()
db_client: AsyncIOMotorClient = None

async def get_db() -> AsyncIOMotorDatabase:
    """
    Returns the database instance.
    Raises HTTPException if the database client is not initialized.
    """
    if db_client is None:
        logging.error("Database client not initialized")
        raise HTTPException(status_code=500, detail="Database connection not available")
    
    db_name = app_settings.MONGO_DB
    return db_client[db_name]


async def connect_and_init_db():
    """
    Initializes the database connection with connection pooling.
    - maxPoolSize: Maximum number of connections in the connection pool
    - minPoolSize: Minimum number of connections in the connection pool
    """
    global db_client
    try:
        db_client = AsyncIOMotorClient(app_settings.MONGO_URL,
            # username=app_settings.MONGO_USER,
            # password=app_settings.MONGO_PASSWORD,
            maxPoolSize=app_settings.MAX_DB_CONN_COUNT,
            minPoolSize=app_settings.MIN_DB_CONN_COUNT,
            uuidRepresentation="standard",
        )
        # Verify connection is working
        await db_client.admin.command('ping')
        logging.info('Connected to MongoDB successfully.')
    except Exception as e:
        logging.exception(f'Could not connect to MongoDB: {e}')
        raise
    
async def close_db_connection():
    """Closes the database connection if it exists."""
    global db_client
    if db_client is None:
        logging.warning('No connection to database, nothing to close')
        return
    db_client.close()
    db_client = None
    logging.info('MongoDB connection closed')