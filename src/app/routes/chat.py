from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database
from app.dependencies.api_key import get_api_key
from app.dependencies.session_token import get_session_data
from app.models.ChatSessionModel import ChatSessionModel
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

chat_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)

class SessionRequest(BaseModel):
    user_id: str
    project_id: str
    expires_in_minutes: Optional[int] = 60

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []
    stream: Optional[bool] = True

@chat_router.post("/sessions", response_model=Dict[str, Any])
async def create_chat_session(
    request: SessionRequest,
    api_key: str = Depends(get_api_key),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new chat session (requires API key)"""
    session_model = ChatSessionModel(db_client=db)
    session = await session_model.create_session(
        user_id=request.user_id,
        project_id=request.project_id,
        expires_in_minutes=request.expires_in_minutes
    )
    
    return {
        "session_token": session["session_token"],
        "expires_at": session["expires_at"].isoformat()
    }

@chat_router.delete("/sessions")
async def revoke_chat_session(
    session_data: Dict[str, Any] = Depends(get_session_data),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Revoke the current chat session"""
    session_model = ChatSessionModel(db_client=db)
    success = await session_model.revoke_session(session_data["token"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )
    
    return {"message": "Session revoked successfully"}

@chat_router.post("/query")
async def chat_query(
    request: ChatRequest,
    session_data: Dict[str, Any] = Depends(get_session_data),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Send a query to the RAG chatbot"""
    # If streaming is requested
    if request.stream:
        return StreamingResponse(
            stream_chat_response(request.query, request.history, session_data),
            media_type="text/event-stream"
        )
    
    # For non-streaming responses
    response = await generate_chat_response(request.query, request.history, session_data)
    return {"response": response}

async def stream_chat_response(query: str, history: List[Dict[str, str]], session_data: Dict[str, Any]):
    """Stream the chat response"""
    # This is where you'd implement your actual LLM streaming logic
    # For demonstration, we'll simulate a streaming response
    response_parts = [
        "I'm ",
        "generating ",
        "a ",
        "streaming ",
        "response ",
        "for ",
        "project ",
        f"{session_data['project_id']}."
    ]
    
    for part in response_parts:
        yield f"data: {part}\n\n"
        await asyncio.sleep(0.2)  # Simulate processing time
    
    yield "data: [DONE]\n\n"

async def generate_chat_response(query: str, history: List[Dict[str, str]], session_data: Dict[str, Any]):
    """Generate a complete chat response"""
    # This is where you'd implement your actual LLM response logic
    return f"This is a non-streaming response for project {session_data['project_id']}" 