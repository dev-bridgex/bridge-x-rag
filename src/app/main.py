from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes import base, data
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings, get_files_dir

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create files directory ( will store projects in ) in the assets directory
    _ = get_files_dir()
    
    # Startup: Connect to the database
    settings = get_settings()
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]
    
    yield  # This is where FastAPI serves requests
    
    # Shutdown: Close the database connection
    app.mongo_conn.close()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)