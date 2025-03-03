from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers import DataController
from models import ResponseSignal

import aiofiles
import logging


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


@data_router.post("/upload/{project_id}", status_code=status.HTTP_201_CREATED)
async def upload_data(
    project_id: str, file: UploadFile, 
    app_settings: Settings = Depends(get_settings)
):
    
    # Validate the file properties and return a signal if not valid
    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
    
    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result_signal}
        )
    
    
    # get a file path in the project directory(project_id) and a unique file name(id) 
    file_path, file_id = data_controller.generate_unique_filepath(
        project_id=project_id,
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
        logging.error(f"Error while uploading file: {e}")
        
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
    

    

