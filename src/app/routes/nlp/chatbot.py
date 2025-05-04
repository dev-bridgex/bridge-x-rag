from fastapi import APIRouter, Depends, Request
from app.logging import get_logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import NLPController
from .service import NLPService
from app.dependencies import get_database, get_knowledge_base_model, get_asset_model, get_chunk_model, get_nlp_controller
from .schemas import ChatRequest, ChatResponse

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
    - use_hybrid: Whether to use hybrid search (vector + text) (default: true)
    - limit: Maximum number of chunks to retrieve (default: 5)
    - use_query_rewriting: Whether to rewrite the query for better retrieval (default: true)
    """


    response, sources = await nlp_service.chat_with_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        query=chat_request.query,
        history=chat_request.history,
        use_rag=chat_request.use_rag,
        use_hybrid=chat_request.use_hybrid,
        limit=chat_request.limit,
        use_query_rewriting=chat_request.use_query_rewriting
    )

    return ChatResponse(
        response=response,
        sources=sources,
        query=chat_request.query,
        knowledge_base_id=knowledge_base_id
    )



