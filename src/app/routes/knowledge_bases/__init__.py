from fastapi import APIRouter
from .crud import router as crud_router


knowledge_base_router = APIRouter(
    prefix="/api/knowledge_bases",
    tags=["knowledge_bases"],
)

# Include sub-routers
knowledge_base_router.include_router(crud_router)
