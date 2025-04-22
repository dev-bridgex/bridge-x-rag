from fastapi import APIRouter
from .vector_db import router as vector_db_router
from .chatbot import router as chatbot_router

nlp_router = APIRouter(
    prefix="/api/nlp",
    tags=["nlp"]
)

# Include the vector database operations router
nlp_router.include_router(vector_db_router)

# Include the chatbot operations router
nlp_router.include_router(chatbot_router)
