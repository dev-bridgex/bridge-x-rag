from fastapi import APIRouter, Depends, UploadFile, status
from app.helpers.config import get_settings, Settings
from app.logging import get_logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import KnowledgeBaseController, AssetController, ProcessingController, NLPController
from app.dependencies import (
    get_database, get_knowledge_base_model, get_asset_model, get_chunk_model,
    get_knowledge_base_controller, get_asset_controller, get_processing_controller, get_nlp_controller
)
from .service import AssetService
from .schemas import (
    AssetDetailResponse, AssetCreateResponse, AssetDeleteResponse,
    PaginatedAssetListResponse, AssetListItem, AssetResponse
)

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

@router.post("/{knowledge_base_id}",
           response_model=AssetCreateResponse,
           status_code=status.HTTP_201_CREATED,
           description="Upload a file as an asset to a specific knowledge base")
async def upload_asset(
    knowledge_base_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
    asset_service: AssetService = Depends(get_asset_service)
):
    # Upload asset using service - returns both asset and knowledge base
    # Service handles exceptions with appropriate status codes and signals
    asset_record, knowledge_base = await asset_service.upload_asset(
        knowledge_base_id=knowledge_base_id,
        file=file,
        chunk_size=app_settings.FILE_DEFAULT_CHUNK_SIZE
    )

    # Create response directly
    return AssetCreateResponse(
        asset_id=str(asset_record.id),
        asset_name=asset_record.asset_name,
        knowledge_base_id=knowledge_base_id,
        knowledge_base_name=knowledge_base.knowledge_base_name
    )


@router.get("/{knowledge_base_id}",
          response_model=PaginatedAssetListResponse,
          description="Get all assets for a specific knowledge base with pagination support")
async def list_assets(
    knowledge_base_id: str,
    asset_type: str = None,
    page: int = 1,
    page_size: int = 10,
    asset_service: AssetService = Depends(get_asset_service)
):
    # Get knowledge base and assets with pagination
    # Service handles exceptions with appropriate status codes and signals
    knowledge_base = await asset_service.validate_knowledge_base(knowledge_base_id=knowledge_base_id)
    assets, total_pages, total_items = await asset_service.get_knowledge_base_assets(
        knowledge_base_id=knowledge_base_id,
        asset_type=asset_type,
        page=page,
        page_size=page_size
    )

    # Create response directly
    # Create asset list items
    asset_list = [AssetListItem(
        id=str(asset.id),
        name=asset.asset_name,
        type=asset.asset_type,
        size=asset.asset_size,
        uploaded_at=asset.asset_pushed_at
    ) for asset in assets]

    # Return response using the updated schema
    return PaginatedAssetListResponse(
        knowledge_base_id=knowledge_base_id,
        knowledge_base_name=knowledge_base.knowledge_base_name,
        assets=asset_list,
        page_number=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/{knowledge_base_id}/asset/{asset_id}",
          response_model=AssetDetailResponse,
          description="Get a specific asset by ID")
async def get_asset(
    knowledge_base_id: str,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service)
):
    # Validate knowledge base and asset
    # Service handles exceptions with appropriate status codes and signals
    knowledge_base, asset = await asset_service.validate_knowledge_base_and_asset(knowledge_base_id=knowledge_base_id, asset_id=asset_id)

    # Create response directly
    # Create asset response
    asset_response = AssetResponse(
        id=str(asset.id),
        name=asset.asset_name,
        type=asset.asset_type,
        size=asset.asset_size,
        path=asset.asset_path,
        uploaded_at=asset.asset_pushed_at,
        knowledge_base_id=str(asset.asset_knowledge_base_id),
        knowledge_base_name=knowledge_base.knowledge_base_name
    )

    # Return response
    return AssetDetailResponse(
        asset=asset_response
    )


@router.delete("/{knowledge_base_id}/asset/{asset_id}",
             response_model=AssetDeleteResponse,
             description="Delete a specific asset by ID")
async def delete_asset(
    knowledge_base_id: str,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service)
):
    # Delete asset using service
    # Service handles exceptions with appropriate status codes and signals
    result = await asset_service.delete_asset_with_resources(
        knowledge_base_id=knowledge_base_id,
        asset_id=asset_id
    )

    # Create response directly
    return AssetDeleteResponse(
        asset_id=result["asset_id"],
        asset_name=result["asset_name"],
        knowledge_base_id=result["knowledge_base_id"],
        knowledge_base_name=result["knowledge_base_name"],
        file_deleted=result["file_deleted"],
        chunks_deleted=result["chunks_deleted"],
        vector_db_deleted=result.get("vector_db_deleted", False)
    )
