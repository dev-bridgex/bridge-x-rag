from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from app.helpers.config import get_settings, Settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database

from .schemas.data import ProcessRequest
from app.models import ResponseSignal
from app.models.ProjectModel import ProjectModel
from app.models.ChunkModel import ChunkModel
from app.models.db_schemas import DataChunk

from app.controllers import DataController, ProcessController, ProjectController

from langchain_core.documents import Document
import aiofiles
import logging
import os


logger = logging.getLogger("uvicorn.info")


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

data_controller = DataController()
process_controller = ProcessController()
project_controller = ProjectController()


@data_router.post("/upload/{project_id}", 
                 status_code=status.HTTP_201_CREATED,
                 description="Upload a file to a specific project")
async def upload_data(
    project_id: str, 
    file: UploadFile, 
    app_settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Validate the file properties - will raise HTTPException if invalid
    data_controller.validate_uploaded_file(file=file)
    
    # Get or create project in database
    project_model = ProjectModel(db_client=db)
    try:
        project = await project_model.get_project_or_create_one(project_id=project_id)
    except Exception as e:
        logger.error(f"Database error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    # Get or create project directory
    project_dir_path = project_controller.get_project_path(project_id=project_id)
    
    file_path, file_id = data_controller.generate_unique_filepath(
        project_path=project_dir_path,
        original_file_name=file.filename
    )
    
    # Save File in project path
    try:
        # Opens the destination file asynchronously 
        async with aiofiles.open(file=file_path, mode="wb") as f:
            # Reads the uploaded file in chunks
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                # write the chunk in the destination file f
                await f.write(chunk)
                
        # Log successful upload
        logger.info(f"File {file_id} successfully uploaded to project {project_id}")
                
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        
        # Try to clean up the file if it was partially written
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            logger.error(f"Failed to clean up file after upload error: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )
        
    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            "file_id": file_id,
            "file_name": file.filename,
            "project_id": str(project.id)
        }
    )
        


@data_router.post("/process/{project_id}", 
                 description="Process a file in a specific project")
async def process_data(
    project_id: str, 
    process_request: ProcessRequest, 
    db: AsyncIOMotorDatabase = Depends(get_database),
    
):
    # extract file_processing request details
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset
        
    # check project with id exists
    project_path = project_controller.find_project_path(project_id=project_id)
    
    if project_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id: {project_id} not found"
        )
        
    # check file exist in the project path
    file_path = process_controller.get_file_path(file_id=file_id, project_path=project_path)
    
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id: {file_id} not found in project: {project_id}"
        )
    
    # Process requested file in the referenced project                                               
    file_content = process_controller.get_file_content(file_id=file_id, file_path=file_path)
    
    file_chunks: list[Document] = process_controller.process_file_content(
        file_content=file_content,
        file_id=file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size
    )
    
    if file_chunks is None or len(file_chunks) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process file content"
        )
        
    # Get Project From MongoDB Project Collection
    
    project_model = ProjectModel(db_client=db)
    try:
        project = await project_model.get_project_or_create_one(project_id=project_id)
    except Exception as e:
        logger.error(f"Database error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    
    # Save Proccessed File's Chunks Documents Into MongoDB Chunks Collection
    
    file_chunks_records: list[Document] = [
        DataChunk(
            chunk_text=chunk.page_content,
            chunk_metadata=chunk.metadata,
            chunk_order=idx+1,
            chunk_project_id=project.id
        )
        for idx, chunk in enumerate(file_chunks)
    ]
     
    chunk_model = ChunkModel(db_client=db)
    
    ### >>> Will Need To Fix this delete later
    if do_reset == 1:
        _ = await chunk_model.delete_chunks_by_project_id(
            project_id=project.id
        )

    no_records = await chunk_model.insert_many_chunks(
        chunks=file_chunks_records
        )
    
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_records
        }
    )


