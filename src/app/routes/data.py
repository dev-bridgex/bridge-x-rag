from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from helpers.config import get_settings, Settings
from controllers import DataController, ProcessController, ProjectController
from models import ResponseSignal
from .schemas.data import ProcessRequest

import aiofiles
import logging

logger = logging.getLogger("uvicorn.error")


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

data_controller = DataController()
process_controller = ProcessController()
project_controller = ProjectController()


@data_router.post("/upload/{project_id}", status_code=status.HTTP_201_CREATED)
async def upload_data(
    project_id: str, file: UploadFile, 
    app_settings: Settings = Depends(get_settings)
):
    
    # Validate the file properties and return a signal if not valid
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
    
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result_signal}
        )
    
    
    # get a file path in the project directory(project_id) and a unique file name(id) 
    project_path = project_controller.get_project_path(project_id=project_id)
    
    file_path, file_id = data_controller.generate_unique_filepath(
        project_path=project_path,
        original_file_name=file.filename
    )
    
    
    # Save File in project path
    try:
        # 1)Opens the destination file asynchronously 
        async with aiofiles.open(file=file_path, mode="wb") as f:
            # Reads the uploaded file in chunks
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                # write the chunk in the distination file f
                await f.write(chunk)
                
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            "file_id": file_id
        }
    )
    

@data_router.post("/process/{project_id}")
async def process_data(project_id: str, process_request: ProcessRequest):
    
    # check project with id exists
    project_path = project_controller.find_project_path(project_id=project_id)
    
    if project_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id: {project_id} dosn't exist!"
        )
        
    # check file exist in the project path
    file_path = process_controller.get_file_path( file_id=process_request.file_id, project_path=project_path )
    
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id: {process_request.file_id} dosn't exist in the Project With id: {project_id}"
        )
    
    # Process requested file in the refrenced project                                               
    file_content = process_controller.get_file_content( file_id=process_request.file_id, file_path=file_path)
    
    file_chunks = process_controller.process_file_content( file_content = file_content,
        file_id = process_request.file_id,
        chunk_size = process_request.chunk_size,
        overlap_size = process_request.overlap_size
    )
    
    if file_chunks is None or len(file_chunks) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value}   
        )

    return file_chunks

