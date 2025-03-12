from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.models.ChatSessionModel import ChatSessionModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database

SESSION_TOKEN_NAME = "X-Session-Token"
session_token_header = APIKeyHeader(name=SESSION_TOKEN_NAME, auto_error=False)

async def get_session_data(
    session_token: str = Security(session_token_header),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing"
        )
    
    session_model = ChatSessionModel(db_client=db)
    session_data = await session_model.validate_session_token(session_token)
    
    if not session_data["valid"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    return session_data 