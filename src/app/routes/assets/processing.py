from fastapi import APIRouter, Depends, status
from app.logging import get_logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import KnowledgeBaseController, AssetController, ProcessingController, NLPController
from app.dependencies import (
    get_database, get_knowledge_base_model, get_asset_model, get_chunk_model,
    get_knowledge_base_controller, get_asset_controller, get_processing_controller, get_nlp_controller
)
from .service import AssetService
from .schemas import KnowledgeBaseProcessRequest, AssetProcessRequest, AssetProcessResponse



logger = get_logger(__name__)

router = APIRouter()

# Dependency for AssetService
async def get_asset_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    knowledge_base_model: KnowledgeBaseModel = Depends(get_knowledge_base_model),
    asset_model: AssetModel = Depends(get_asset_model),
    chunk_model: ChunkModel = Depends(get_chunk_model),
    knowledge_base_controller: KnowledgeBaseController = Depends(get_knowledge_base_controller),
    asset_controller: AssetController = Depends(get_asset_controller),
    processing_controller: ProcessingController = Depends(get_processing_controller),
    nlp_controller: NLPController = Depends(get_nlp_controller)
):
    return AssetService(
        db=db,
        knowledge_base_model=knowledge_base_model,
        asset_model=asset_model,
        chunk_model=chunk_model,
        knowledge_base_controller=knowledge_base_controller,
        asset_controller=asset_controller,
        processing_controller=processing_controller,
        nlp_controller=nlp_controller
    )


@router.post("/process/{knowledge_base_id}",
           response_model=AssetProcessResponse,
           status_code=status.HTTP_200_OK,
           description="Process all assets in a knowledge base")
async def process_knowledge_base_assets(
    knowledge_base_id: str,
    process_request: KnowledgeBaseProcessRequest,
    asset_service: AssetService = Depends(get_asset_service)
):
    # Process all assets in the knowledge base
    # Service handles exceptions with appropriate status codes and signals
    result = await asset_service.process_assets(
        knowledge_base_id=knowledge_base_id,
        chunk_size=process_request.chunk_size,
        overlap_size=process_request.overlap_size,
        do_reset=process_request.do_reset,
        reset_vector_db=process_request.reset_vector_db,
        skip_duplicates=process_request.skip_duplicates,
        batch_size=process_request.batch_size if hasattr(process_request, 'batch_size') else 50
    )

    # Create response directly
    return AssetProcessResponse(
        processed_files=result["processed_files"],
        inserted_chunks=result["inserted_chunks"],
        total_assets=result.get("total_assets")  # Only present for batch processing
    )


@router.post("/process/{knowledge_base_id}/asset/{asset_id}",
           response_model=AssetProcessResponse,
           status_code=status.HTTP_200_OK,
           description="Process a specific asset by ID with customizable chunking parameters")
async def process_asset_by_id(
    knowledge_base_id: str,
    asset_id: str,
    process_request: AssetProcessRequest,
    asset_service: AssetService = Depends(get_asset_service)
):
    # Process specific asset using the dedicated service method
    # Service handles exceptions with appropriate status codes and signals
    result = await asset_service.process_single_asset(
        knowledge_base_id=knowledge_base_id,
        asset_id=asset_id,
        chunk_size=process_request.chunk_size,
        overlap_size=process_request.overlap_size,
        do_reset=process_request.do_reset,
        reset_vector_db=process_request.reset_vector_db,
        skip_duplicates=process_request.skip_duplicates
    )

    # Create response directly
    return AssetProcessResponse(
        processed_files=result["processed_files"],
        inserted_chunks=result["inserted_chunks"]
    )