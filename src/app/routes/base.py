from fastapi import APIRouter, Depends
from app.helpers.config import get_settings, Settings

base_router = APIRouter(
    prefix="/api",
    # tags=["api_v1"],
)

@base_router.get("/")
async def welcome(app_settings: Settings = Depends(get_settings)):
    
    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION
    
    return {
        "app_name": app_name,
        "app_version": app_version
    }

@base_router.get("/health")
async def health_check():
    return {"status": "healthy"}