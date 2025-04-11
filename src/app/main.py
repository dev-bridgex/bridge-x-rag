from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.routes import base, data, nlp

from app.helpers.config import get_settings, init_database_dir, init_files_dir
from app.db.mongodb import connect_and_init_db, close_db_connection

from app.logging import setup_logging, get_logger
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.logging_middleware import logging_middleware
# from app.exception_handlers import http_exception_handler, validation_exception_handler

from app.stores.llm import LLMProviderFactory
from app.stores.vectordb import VectorDBProviderFactory

from app.testing_vectordb import test_qdrant


# Initialize application settings
app_settings = get_settings()

# Set up logging first thing
logger = setup_logging(log_level=logging.INFO)
module_logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup: Create files directory (will store projects in) in the assets directory
        files_dir = init_files_dir()
        database_dir = init_database_dir()
        module_logger.info(f"Files directory initialized at: {files_dir}")
        module_logger.info(f"Database directory initialized at: {database_dir}")
        
        # Startup: Connect to the database
        module_logger.info("Initializing database connection...")
        await connect_and_init_db()
        
        # initialize providers
        llm_provider_factory = LLMProviderFactory(config = app_settings)
        vectordb_provider_factory = VectorDBProviderFactory(config = app_settings)
        
        # init Generation client
        app.generation_client= llm_provider_factory.create(provider=app_settings.GENERATION_BACKEND)
        app.generation_client.set_generation_model(model_id=app_settings.GENERATION_MODEL_ID)
        
        # init Embedding client
        app.embedding_client = llm_provider_factory.create( provider=app_settings.EMBEDDING_BACKEND )
        app.embedding_client.set_embedding_model(
            model_id=app_settings.EMBEDDING_MODEL_ID, embedding_size=app_settings.EMBEDDING_MODEL_SIZE
            )
        
        # init Vector Db client
        
        app.vectordb_client = vectordb_provider_factory.create(
            provider = app_settings.VECTOR_DB_BACKEND
        )
        
        # Uses async context manager (__aenter__ / __aexit__) to connect to the vector db client    
        async with app.vectordb_client:
            # test vector db client 
            # await test_qdrant(app.vectordb_client)
             
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
app.include_router(nlp.nlp_router)


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

