from fastapi import APIRouter, Depends, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.logging import get_logger
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import NLPController
from .service import NLPService
from .schemas import ChatRequest, ChatResponse, RAGAnswerRequest, RAGAnswerResponse
from app.dependencies import get_knowledge_base_model, get_asset_model, get_chunk_model, get_nlp_controller

logger = get_logger(__name__)

router = APIRouter()

# Dependency for NLPService
async def get_nlp_service(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
    knowledge_base_model: KnowledgeBaseModel = Depends(get_knowledge_base_model),
    asset_model: AssetModel = Depends(get_asset_model),
    chunk_model: ChunkModel = Depends(get_chunk_model),
    nlp_controller: NLPController = Depends(get_nlp_controller)
):
    return NLPService(db=db, request=request, knowledge_base_model=knowledge_base_model, asset_model=asset_model, chunk_model=chunk_model, nlp_controller=nlp_controller)


# ChatResponse is now defined in schemas.py


@router.post("/knowledge-bases/{knowledge_base_id}/chat",
           response_model=ChatResponse,
           description="Chat with a knowledge base using RAG")
async def chat_with_knowledge_base(
    knowledge_base_id: str,
    chat_request: ChatRequest,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """
    Chat with a knowledge base using RAG

    This endpoint allows for conversational interaction with a knowledge base.
    It can use RAG (Retrieval-Augmented Generation) to provide context-aware responses
    based on the content of the knowledge base.

    - query: The user's message or question
    - history: Previous chat history (optional)
    - use_rag: Whether to use retrieval for context (default: true)
    - limit: Maximum number of chunks to retrieve (default: 5)
    """
    response, sources = await nlp_service.chat_with_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        query=chat_request.query,
        history=chat_request.history,
        use_rag=chat_request.use_rag,
        limit=chat_request.limit
    )

    return {
        "response": response,
        "sources": sources,
        "query": chat_request.query,
        "knowledge_base_id": knowledge_base_id
    }


@router.post("/knowledge-bases/{knowledge_base_id}/answer",
           response_model=RAGAnswerResponse,
           description="Answer a question using RAG")
async def answer_rag_query(
    knowledge_base_id: str,
    rag_request: RAGAnswerRequest,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """
    Answer a question using RAG (Retrieval-Augmented Generation)

    This endpoint retrieves relevant chunks from the knowledge base based on the query,
    then uses an LLM to generate a comprehensive answer based on those chunks.

    - query: The question to answer
    - limit: Maximum number of chunks to retrieve (default: 5)
    """
    answer, full_prompt, chat_history = await nlp_service.answer_rag_query(
        knowledge_base_id=knowledge_base_id,
        query=rag_request.query,
        limit=rag_request.limit,
    )

    return {
        "answer": answer,
        "full_prompt": full_prompt,
        "chat_history": chat_history,
        "query": rag_request.query,
        "knowledge_base_id": knowledge_base_id
    }
