from fastapi import APIRouter, Depends, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.logging import get_logger
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import NLPController
from .service import NLPService
from .schemas import (
    KnowledgeBaseIndexRequest, SearchRequest, AssetIndexRequest,
    IndexOperationResponse, CollectionInfoResponse, SearchResponse, AssetIndexResponse,
    AssetDeleteResponse
)
# Response helpers have been removed - responses are now created directly
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


@router.post("/knowledge-bases/{knowledge_base_id}/index",
           response_model=IndexOperationResponse,
           status_code=status.HTTP_201_CREATED,
           description="Index a knowledge base's chunks into vector database")
async def index_knowledge_base(
    knowledge_base_id: str,
    index_request: KnowledgeBaseIndexRequest,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    # Service handles exceptions with appropriate status codes and signals
    result = await nlp_service.index_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        do_reset=index_request.do_reset,
        skip_duplicates=index_request.skip_duplicates
    )

    # Create response directly
    return IndexOperationResponse(
        inserted_items_count=result["inserted_items_count"]
    )


@router.post("/knowledge-bases/{knowledge_base_id}/assets/{asset_id}/index",
           response_model=AssetIndexResponse,
           status_code=status.HTTP_201_CREATED,
           description="Index a specific asset into vector database")
async def index_asset(
    knowledge_base_id: str,
    asset_id: str,
    index_request: AssetIndexRequest,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    # Service handles exceptions with appropriate status codes and signals
    result = await nlp_service.index_asset(
        knowledge_base_id=knowledge_base_id,
        asset_id=asset_id,
        do_reset=index_request.do_reset,
        skip_duplicates=index_request.skip_duplicates
    )

    # Create response directly
    return AssetIndexResponse(
        asset_id=result["asset_id"],
        knowledge_base_id=result["knowledge_base_id"],
        indexed_chunks_count=result["indexed_chunks_count"]
    )


@router.get("/knowledge-bases/{knowledge_base_id}/info",
          response_model=CollectionInfoResponse,
          description="Get information about a knowledge base's vector database collection")
async def get_collection_info(
    knowledge_base_id: str,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    # Service handles exceptions with appropriate status codes and signals
    result = await nlp_service.get_collection_info(knowledge_base_id=knowledge_base_id)

    # Create response directly
    return CollectionInfoResponse(
        collection_info=result["index_collection_info"]
    )


@router.delete("/knowledge-bases/{knowledge_base_id}/assets/{asset_id}",
             response_model=AssetDeleteResponse,
             description="Delete a specific asset from vector database")
async def delete_asset_from_index(
    knowledge_base_id: str,
    asset_id: str,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    # Service handles exceptions with appropriate status codes and signals
    result = await nlp_service.delete_asset_from_index(
        knowledge_base_id=knowledge_base_id,
        asset_id=asset_id
    )

    # Create response directly
    return AssetDeleteResponse(
        asset_id=result["asset_id"],
        knowledge_base_id=result["knowledge_base_id"],
        deleted_from_vector_db=result["deleted_from_vector_db"]
    )


@router.post("/knowledge-bases/{knowledge_base_id}/search",
           response_model=SearchResponse,
           description="Perform semantic search in a knowledge base's vector database collection")
async def search_knowledge_base(
    knowledge_base_id: str,
    search_request: SearchRequest,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    # Service handles exceptions with appropriate status codes and signals
    results = await nlp_service.search_collection(
        knowledge_base_id=knowledge_base_id,
        query=search_request.query,
        limit=search_request.limit
    )

    # Create response directly
    return SearchResponse(
        results=results
    )
