from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.logging import get_logger
from app.controllers import NLPController, KnowledgeBaseController
from app.models import KnowledgeBaseModel
from .service import KnowledgeBaseService
from app.dependencies import get_knowledge_base_model, get_knowledge_base_controller, get_nlp_controller
from .schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, PaginatedKnowledgeBaseListResponse,
    KnowledgeBaseDetailResponse, KnowledgeBaseCreateResponse, KnowledgeBaseUpdateResponse,
    KnowledgeBaseDeleteResponse, KnowledgeBaseListItem, KnowledgeBaseResponse
)
# Response helpers have been removed - responses are now created directly

logger = get_logger(__name__)

router = APIRouter()

# Dependency for KnowledgeBaseService
async def get_knowledge_base_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    knowledge_base_model: KnowledgeBaseModel = Depends(get_knowledge_base_model),
    knowledge_base_controller: KnowledgeBaseController = Depends(get_knowledge_base_controller),
    nlp_controller: NLPController = Depends(get_nlp_controller)
):
    return KnowledgeBaseService(
        db=db,
        knowledge_base_model=knowledge_base_model,
        knowledge_base_controller=knowledge_base_controller,
        nlp_controller=nlp_controller
    )


@router.post("/",
           response_model=KnowledgeBaseCreateResponse,
           status_code=status.HTTP_201_CREATED,
           description="Create a new knowledge base")
async def create_knowledge_base(
    knowledge_base_data: KnowledgeBaseCreate,
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    # Create knowledge base - service handles exceptions
    knowledge_base = await knowledge_base_service.create_knowledge_base(knowledge_base_name=knowledge_base_data.knowledge_base_name)

    # Create response directly
    return KnowledgeBaseCreateResponse(
        knowledge_base_id=str(knowledge_base.id),
        knowledge_base_name=knowledge_base.knowledge_base_name
    )


@router.get("/",
          response_model=PaginatedKnowledgeBaseListResponse,
          description="Get all knowledge bases with pagination or filter by ID")
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 10,
    knowledge_base_id: str = None,  # Optional: Filter by knowledge base ID
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    # If knowledge_base_id is provided, filter by ID
    if knowledge_base_id:
        # Get the specific knowledge base
        try:
            knowledge_base = await knowledge_base_service.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
            # Create a list with just this knowledge base
            knowledge_bases = [knowledge_base]
            total_pages = 1
            total_items = 1
        except Exception:
            # If knowledge base not found, return empty list
            knowledge_bases = []
            total_pages = 0
            total_items = 0
    else:
        # Get all knowledge bases with pagination - service handles exceptions
        knowledge_bases, total_pages, total_items = await knowledge_base_service.get_all_knowledge_bases(page=page, page_size=page_size)

    # Create response directly
    # Create knowledge base list items
    kb_list = [KnowledgeBaseListItem(
        id=str(kb.id),
        knowledge_base_name=kb.knowledge_base_name,
        created_at=kb.created_at,
        updated_at=kb.updated_at
    ) for kb in knowledge_bases]

    # Return response
    return PaginatedKnowledgeBaseListResponse(
        knowledge_bases=kb_list,
        page_number=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/{knowledge_base_id}",
          response_model=KnowledgeBaseDetailResponse,
          description="Get a specific knowledge base by ID")
async def get_knowledge_base(
    knowledge_base_id: str,
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    # Get knowledge base - service handles exceptions
    knowledge_base = await knowledge_base_service.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)

    # Create response directly
    # Create knowledge base response
    kb_response = KnowledgeBaseResponse(
        id=str(knowledge_base.id),
        knowledge_base_name=knowledge_base.knowledge_base_name,
        knowledge_base_dir_path=knowledge_base.knowledge_base_dir_path,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at
    )

    # Return response
    return KnowledgeBaseDetailResponse(
        knowledge_base=kb_response
    )


@router.put("/{knowledge_base_id}",
          response_model=KnowledgeBaseUpdateResponse,
          description="Update a knowledge base")
async def update_knowledge_base(
    knowledge_base_id: str,
    knowledge_base_update: KnowledgeBaseUpdate,
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    # The service now handles the case when knowledge_base_name is None

    # Update knowledge base (NLPController is already injected into the service)
    updated_knowledge_base, resources_updated = await knowledge_base_service.update_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        knowledge_base_name=knowledge_base_update.knowledge_base_name
    )

    # Create response directly
    return KnowledgeBaseUpdateResponse(
        knowledge_base_id=str(updated_knowledge_base.id),
        knowledge_base_name=updated_knowledge_base.knowledge_base_name,
        resources_updated=resources_updated
    )


@router.delete("/{knowledge_base_id}",
             response_model=KnowledgeBaseDeleteResponse,
             description="Delete a knowledge base and all its resources")
async def delete_knowledge_base(
    knowledge_base_id: str,
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    # Delete knowledge base (NLPController is already injected into the service)
    # Service handles exceptions
    result = await knowledge_base_service.delete_knowledge_base(
        knowledge_base_id=knowledge_base_id
    )

    # Create response directly
    return KnowledgeBaseDeleteResponse(
        knowledge_base_id=result["knowledge_base_id"],
        knowledge_base_name=result["knowledge_base_name"],
        resources_deleted=result["resources_deleted"],
        vector_db_deleted=result.get("vector_db_deleted", False),
        directory_deleted=result.get("directory_deleted", False),
        assets_deleted=result["assets_deleted"],
        chunks_deleted=result["chunks_deleted"]
    )
