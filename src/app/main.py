from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.routes import base, data
from app.helpers.config import get_files_dir, get_settings
from app.db.mongodb import connect_and_init_db, close_db_connection
from app.core.logging import setup_logging, get_logger
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.logging import logging_middleware
# from app.exception_handlers import http_exception_handler, validation_exception_handler

# Initialize application settings
app_settings = get_settings()

# Set up logging first thing
logger = setup_logging(log_level=logging.INFO)
module_logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup: Create files directory (will store projects in) in the assets directory
        files_dir = get_files_dir()
        module_logger.info(f"Files directory initialized at: {files_dir}")
        
        # Startup: Connect to the database
        module_logger.info("Initializing database connection...")
        await connect_and_init_db()
        
        module_logger.info(f"Application startup complete: {app_settings.APP_NAME} v{app_settings.APP_VERSION}")
        
        yield  # This is where FastAPI serves requests
        
    except Exception as e:
        module_logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise
    finally:
        # Shutdown: Close the database connection
        try:
            module_logger.info("Shutting down database connection...")
            await close_db_connection()
            module_logger.info("Application shutdown complete")
        except Exception as e:
            module_logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

app = FastAPI(
    lifespan=lifespan,
    title=app_settings.APP_NAME,
    description="API for the Bridge-X-RAG application",
    version=app_settings.APP_VERSION,
)

# Register exception handlers
# app.add_exception_handler(HTTPException, http_exception_handler)
# app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Register app routers
app.include_router(base.base_router)
app.include_router(data.data_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware - Uncomment to enable request logging
app.middleware("http")(logging_middleware)

module_logger.info(f"Application initialized and ready to handle requests")