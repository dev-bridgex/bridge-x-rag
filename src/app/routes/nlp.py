from fastapi import APIRouter, status, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from app.helpers.config import Settings, get_settings
from app.db.mongodb import get_database
from app.logging import get_logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from .schemas.nlp import PushRequest, SearchRequest, ChatRequest
from app.models import ProjectModel, ChunkModel, ResponseSignalEnum
from app.controllers import NLPController

from tqdm.auto import tqdm



logger = get_logger(__name__)



nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["nlp"]
)

@nlp_router.post("/index/push/{project_name}")
async def index_project(
    request: Request, 
    project_name: str,
    push_request: PushRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
    ):
    
    # Create DataModels Dependency
    project_model = await ProjectModel.create_instance( db_client=db )
    chunk_model = await ChunkModel.create_instance( db_client=db )
    
    # 1. Check project exists in the database
    project = await project_model.get_project_by_name(project_name=project_name)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with With Name : {project_name} not found"
        )
    
    
    # 2. init nlp controller
    nlp_controller = NLPController(
        vectordb_client = request.app.vectordb_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client
    )
    
    # 3. get project chunks and bulk index them into vectordb
    
    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0
    
    # Create vector db collection for the project if not exists
    collection_name = await nlp_controller.create_vector_db_collection(
        project=project, do_reset=push_request.do_reset
        )
    
    if not collection_name:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignalEnum.INDEXING_PROJECT_INTO_VECTORDB_ERROR.value
            }
        )
    
    # setup bacthing 
    total_chunks_count = await chunk_model.get_chunks_count_by_project_id(project_id=project.id)
    pbar = tqdm(total=total_chunks_count, desc="Vector Indexing", position=0)
    
    while has_records:
        page_chunks = await chunk_model.get_chunks_by_project_id(
            project_id=project.id, page= page_no
            )
        
        len_page_chunks = len(page_chunks)
        if len_page_chunks:
            page_no +=1 
        
        # break from the loop if not chunks left to process
        if not page_chunks or len_page_chunks == 0:
            has_records = False
            break
        
        chunks_ids = list(range(idx, idx + len_page_chunks))
        idx += len_page_chunks
        
        is_inserted = await nlp_controller.index_into_vector_db(
            collection_name=collection_name,
            chunks=page_chunks,
            chunks_ids=chunks_ids,
        )
        
        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignalEnum.INSERT_INTO_VECTORDB_ERROR.value
                }
            )
            
        pbar.update(len_page_chunks)
        inserted_items_count += len_page_chunks
        
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "signal": ResponseSignalEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count
        }
    )
    


@nlp_router.get("/index/info/{project_name}")
async def get_project_index_info(
    request: Request, 
    project_name: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
    ):
    
    # Create DataModels Dependency
    project_model = await ProjectModel.create_instance( db_client=db )
    
    # 1. Check project exists in the database
    project = await project_model.get_project_by_name(project_name=project_name)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with With Name : {project_name} not found"
        )
    
    # 2. init nlp controller
    nlp_controller = NLPController(
        vectordb_client = request.app.vectordb_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client
    )
    
    index_collection_info = await nlp_controller.get_vector_db_collection_info( project=project )
    
    if not index_collection_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "signal": f"Error while retrieving the index collection info of the specified project: {project_name}. Please index the project first then try again."
            }
        )
    
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.VECTORDB_COLLECTION_RETRIEVED.value,
            "index_collection_info": index_collection_info
        }
    )
    
    
@nlp_router.post("/index/search/{project_name}")
async def search_project_index(
    request: Request,
    project_name: str,
    search_request: SearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
    ):
    
    # Create DataModels Dependency
    project_model = await ProjectModel.create_instance( db_client=db )
    
    # 1. Check project exists in the database
    project = await project_model.get_project_by_name(project_name=project_name)
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with With Name : {project_name} not found"
        )
    
    # 2. init nlp controller
    nlp_controller = NLPController(
        vectordb_client = request.app.vectordb_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client
    )
    
    
    # 3. check if the provided project was indexed (has a collection) in the vector db or not
    
    collection_exists = await nlp_controller.is_collection_exists( project=project )
    
    if not collection_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "signal": f"Error while retrieving the index_collection of the specified project: {project_name}. Please index the project first then try again."
            }
        )
    
    # 4. perform semantic search in the vector database in (project_index_collection)
    
    results = await nlp_controller.search_vector_db_collection(
        project=project,
        query=search_request.query,
        limit=search_request.limit
    )
    
    if not results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignalEnum.VECTORDB_SEARCH_ERROR.value
            }
        )
                
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.VECTORDB_SEARCH_SUCCESS.value,
            "results": [ result.dict() for result in results ]
        }
    )
