from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.models.ApiKeyModel import ApiKeyModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key header missing"
        )
    
    api_key_model = ApiKeyModel(db_client=db)
    is_valid = await api_key_model.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    return api_key 