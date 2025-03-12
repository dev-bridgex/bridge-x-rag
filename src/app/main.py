from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.routes import base, data, auth, admin, chat
from app.helpers.config import get_files_dir, get_settings
from app.db.mongodb import connect_and_init_db, close_db_connection
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.logging import logging_middleware
from app.exception_handlers import http_exception_handler, validation_exception_handler

app_settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup: Create files directory (will store projects in) in the assets directory
        _ = get_files_dir()
        
        # Startup: Connect to the database
        await connect_and_init_db()
        
        yield  # This is where FastAPI serves requests
    except Exception as e:
        logging.error(f"Error during startup: {str(e)}")
        raise
    finally:
        # Shutdown: Close the database connection
        try:
            await close_db_connection()
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")

app = FastAPI(
    lifespan=lifespan,
    title=app_settings.APP_NAME,
    description="API for the Bridge-X-RAG application",
    version=app_settings.APP_VERSION,
)

# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(auth.auth_router)
app.include_router(admin.admin_router)
app.include_router(chat.chat_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
app.middleware("http")(logging_middleware)