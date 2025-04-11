from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from app.helpers.config import get_settings, Settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.logging import get_logger

from .schemas.data import ProcessRequest
from app.models import ResponseSignalEnum, FileTypesEnum, ProjectModel, AssetModel, ChunkModel
from app.models.db_schemas import Project, Asset, DataChunk

from app.controllers import DataController, ProcessController, ProjectController

from langchain_core.documents import Document
import aiofiles
import os
from datetime import datetime, timezone


logger = get_logger(__name__)


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
)

data_controller = DataController()
process_controller = ProcessController()
project_controller = ProjectController()


@data_router.post("/upload/{project_name}", 
                 status_code=status.HTTP_201_CREATED,
                 description="Upload a file to a specific project to be processed later")
async def upload_data(
    project_name: str, 
    file: UploadFile, 
    app_settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    
    ## 1. Validate the file properties - will raise HTTPException if invalid
    data_controller.validate_uploaded_file(file=file)
    
    ## 2. Get or create project directory
    project_dir_path = project_controller.get_project_path(project_name=project_name)
    
    file_path, file_name = data_controller.generate_unique_filepath(
        project_path=project_dir_path,
        original_file_name=file.filename
    )
    
    ## 3. Get or create project record in the database
    project_model = await ProjectModel.create_instance( db_client=db )
    try:
        project = await project_model.get_project_by_name( project_name=project_name )
        if project == None:
            project_resource = Project(
                project_name=project_name, 
                project_dir_path=project_dir_path,
                created_at=datetime.now(timezone.utc)
                )
            project = await project_model.create_project(project=project_resource)

    except Exception as e:
        logger.error(f"Database error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    
    ## 4. Save the file in project the associated project directory
    try:
        # Opens the destination file asynchronously 
        async with aiofiles.open(file=file_path, mode="wb") as f:
            # Reads the uploaded file in chunks
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                # write the chunk in the destination file f
                await f.write(chunk)
                
        # Log successful upload
        logger.info(f"File with name {file_name} successfully uploaded to project {project_name}")
                
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
        
        
    
    ## 5. Store the file in the database assets collection
    asset_model = await AssetModel.create_instance( db_client=db )
    
    asset_resource = Asset(
        asset_project_id=project.id,
        asset_path=file_path,
        asset_type=file.content_type,
        asset_name=file_name,
        asset_size=file.size
    )
    
    asset_record = await asset_model.create_asset(asset=asset_resource)

    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.FILE_UPLOAD_SUCCESS.value,
            "file_id": str(asset_record.id),
            "file_name": asset_record.asset_name,
            "project_name": project_name
        }
    )
        


@data_router.post("/process/{project_name}", 
                 description="Process a file/files in a specific project")
async def process_data(
    project_name: str, 
    process_request: ProcessRequest, 
    db: AsyncIOMotorDatabase = Depends(get_database),
    
):
    # file_name = process_request.file_name
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset
    
    # Create DataModels Dependency
    asset_model = await AssetModel.create_instance( db_client=db )
    project_model = await ProjectModel.create_instance( db_client=db )
    chunk_model = await ChunkModel.create_instance( db_client=db )
    
    # 1. get project from the database 
    project = await project_model.get_project_by_name(project_name=project_name)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with With Name : {project_name} not found"
        )    
        
    # 2. check project path exists in the storage
    project_path = project_controller.find_project_path(project_name=project_name)
    # project_path = os.path.exists(project.project_dir_path)
    
    if project_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with name : {project_name} not found in the file storage"
        )
        
    
    # 3.  Process File if file_id is provided else process all project files
    
    project_assets_ids_names = {}
    if process_request.file_name:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.id,
            asset_name=process_request.file_name
        )
        
        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "signal": ResponseSignalEnum.FILE_ID_ERROR.value
                }
            ) 
        
        project_assets_ids_names = {
            asset_record.id: asset_record.asset_name
        }
        
        # check file exist in the project path
        file_path = process_controller.get_file_path(file_name=asset_record.asset_name, project_path=project_path)
        if file_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with name: {process_request.file_name} not found in project: {project_name} path"
            )
        
    else:
        
        project_files: list[Asset] = await asset_model.get_all_project_assets(
            asset_project_id=project.id
        )
        
        project_assets_ids_names = {
            record.id: record.asset_name
            for record in project_files
        }
        
    if len(project_assets_ids_names) == 0:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "signal": ResponseSignalEnum.NO_FILES_ERROR.value
            }
        )
    

    # 4. Process requested file/files in the referenced project
    
    no_records = 0
    no_files = 0
    
    ####### >>>> TODO Fix the reset of the hole project if a process request for one file with reset is requested
    
    # reset file chunks if file id is provided with reset flag is True(1)
    if process_request.file_name:
        if do_reset == 1:
            
            assets_ids_names = [ (id,name) for id, name in  project_assets_ids_names.items()]
            asset_id, asset_name = assets_ids_names[0]
            
            _ = await chunk_model.delete_chunks_by_project_and_asset_id(
                project_id=project.id, asset_id= asset_id
            )
    # reset all project files chunks if no file_id provided and reset flag is True(1)
    else: 
        if do_reset == 1:
            
            _ = await chunk_model.delete_chunks_by_project_id(
                project_id=project.id
            )  
    
    # Loop Over the project assets to process them one by one        
    for asset_id, asset_name in project_assets_ids_names.items():
        
        # check the file path exists in the file storage and log the error if not found
        file_path = process_controller.get_file_path(file_name=asset_name, project_path=project_path)
        if file_path is None:
            logger.error(f"Error: asset with id: {asset_id} and name: {asset_name} not Found in the Project: {project_name}")
            continue    
        
        # get the file content as a list of documents[pages with metadata]
        file_content = process_controller.get_file_content(file_name=asset_name, file_path=file_path)
        if file_content is None:
            logger.error(f"Error While Processing file: {asset_name} in the requested project: {project_name}") 
            continue
        
        # process the file documents to splitt them into smaller chunks -> smaller documents
        file_chunks: list[Document] = process_controller.process_file_content(
            file_content=file_content,
            file_name=asset_name,
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )
        
        if file_chunks is None or len(file_chunks) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process file content"
            )
            
        # Save Proccessed File's documents chunks Into MongoDB Chunks Collection
        
        file_chunks_records: list[Document] = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=idx+1,
                chunk_project_id=project.id,
                chunk_asset_id=asset_id
            )
            for idx, chunk in enumerate(file_chunks)
        ]        

        no_records += await chunk_model.insert_many_chunks( chunks=file_chunks_records )
        no_files += 1
        
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignalEnum.PROCESSING_SUCCESS.value,
            "processed_files": no_files,
            "inserted_chunks": no_records
        }
    )


