import os 
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.helpers.config import get_settings
from fastapi import HTTPException
from urllib.parse import quote_plus
from app.core.logging import get_logger

# Get a logger specific to this module
logger = get_logger(__name__)

app_settings = get_settings()
DATABASE_PASSWORD = quote_plus(app_settings.MONGODB_PASSWORD)

# Create a proper connection string with correct authSource
MONGODB_URL = f"mongodb://{app_settings.MONGODB_USERNAME}:{DATABASE_PASSWORD}@{app_settings.MONGODB_HOST}:{app_settings.MONGODB_PORT}/{app_settings.MONGODB_DATABASE}?authSource={app_settings.MONGODB_DATABASE}"

# Add more detailed connection info logging (without exposing the password)
safe_url = f"mongodb://{app_settings.MONGODB_USERNAME}:****@{app_settings.MONGODB_HOST}:{app_settings.MONGODB_PORT}/{app_settings.MONGODB_DATABASE}"
logger.debug(f"MongoDB connection string (redacted): {safe_url}")

db_client: AsyncIOMotorClient = None


async def get_db() -> AsyncIOMotorDatabase:
    """
    Returns the database instance.
    Raises HTTPException if the database client is not initialized.
    """
    if db_client is None:
        logger.error("Database client not initialized")
        raise HTTPException(status_code=500, detail="Database connection not available")
    
    db_name = app_settings.MONGODB_DATABASE
    return db_client[db_name]


async def connect_and_init_db():
    """
    Initializes the database connection with connection pooling.
    - maxPoolSize: Maximum number of connections in the connection pool
    - minPoolSize: Minimum number of connections in the connection pool
    """
    global db_client
    try:
        logger.info(f"Connecting to MongoDB at {app_settings.MONGODB_HOST}:{app_settings.MONGODB_PORT}...")
        # Fix: Remove duplicate username/password parameters
        db_client = AsyncIOMotorClient(
            MONGODB_URL,
            maxPoolSize=app_settings.MAX_DB_CONN_COUNT,
            minPoolSize=app_settings.MIN_DB_CONN_COUNT,
            uuidRepresentation="standard",
        )
        # Verify connection is working by pinging the database we're connecting to
        # instead of the admin database
        logger.info(f"Pinging database '{app_settings.MONGODB_DATABASE}' to verify connection...")
        await db_client[app_settings.MONGODB_DATABASE].command('ping')
        logger.info('Connected to MongoDB successfully!')
        
        # Additional connection info
        server_info = await db_client.server_info()
        logger.info(f"Connected to MongoDB version: {server_info.get('version', 'unknown')}")
        
        # Log database stats
        db = db_client[app_settings.MONGODB_DATABASE]
        stats = await db.command('dbStats')
        logger.info(f"Database stats: {stats.get('collections', 0)} collections, "
                   f"{stats.get('objects', 0)} objects, "
                   f"{stats.get('dataSize', 0) / (1024*1024):.2f} MB data size")
        
        return db_client
    except Exception as e:
        logger.exception(f'Could not connect to MongoDB: {e}')
        raise
    
async def close_db_connection():
    """Closes the database connection if it exists."""
    global db_client
    if db_client is None:
        logger.warning('No connection to database, nothing to close')
        return
    db_client.close()
    db_client = None
    logger.info('MongoDB connection closed')