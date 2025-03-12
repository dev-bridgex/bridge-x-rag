from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database
from app.models.ApiKeyModel import ApiKeyModel
from app.auth.utils import get_current_active_user
from app.models.db_schemes.user import User
from pydantic import BaseModel
from typing import Optional, List

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)

class ApiKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ApiKeyResponse(BaseModel):
    name: str
    description: Optional[str]
    key: str
    created_at: str

@admin_router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new API key (admin only)"""
    # In a real app, check if user has admin role
    
    api_key_model = ApiKeyModel(db_client=db)
    key = await api_key_model.create_api_key(
        name=key_data.name,
        description=key_data.description
    )
    
    return {
        "name": key["name"],
        "description": key["description"],
        "key": key["key"],
        "created_at": key["created_at"].isoformat()
    }

@admin_router.delete("/api-keys/{api_key}")
async def revoke_api_key(
    api_key: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Revoke an API key (admin only)"""
    # In a real app, check if user has admin role
    
    api_key_model = ApiKeyModel(db_client=db)
    success = await api_key_model.revoke_api_key(api_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}

@admin_router.get("/api-keys", response_model=List[dict])
async def list_api_keys(
    skip: int = 0, 
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all API keys (admin only)"""
    # In a real app, check if user has admin role
    
    api_key_model = ApiKeyModel(db_client=db)
    keys = await api_key_model.get_api_keys(skip=skip, limit=limit)
    
    return keys

@admin_router.get("/api-keys/{key_id}", response_model=dict)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get details of a specific API key (admin only)"""
    # In a real app, check if user has admin role
    
    api_key_model = ApiKeyModel(db_client=db)
    key = await api_key_model.get_api_key_by_id(key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return key 