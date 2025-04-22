from fastapi import APIRouter
from .crud import router as crud_router
from .processing import router as processing_router

asset_router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
)

# Include sub-routers
asset_router.include_router(crud_router)
asset_router.include_router(processing_router)
