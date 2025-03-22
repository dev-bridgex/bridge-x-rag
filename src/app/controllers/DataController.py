from fastapi import UploadFile, status, HTTPException
from .BaseController import BaseController
import re
import os
import logging

logger = logging.getLogger(__name__)

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 # Convert MB to Bytes
        
    def validate_uploaded_file(self, file: UploadFile):
        """
        Validates the uploaded file.
        Raises HTTPException if validation fails.
        """
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type {file.content_type} not supported. Allowed types: {self.app_settings.FILE_ALLOWED_TYPES}"
            )
        
        # Check file size - handle case where size might be None
        file_size = file.size
        if file_size is None:
            # Try to determine size by reading and seeking back
            try:
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()  # Get position (size)
                file.file.seek(0)  # Seek back to beginning
            except Exception as e:
                logger.warning(f"Could not determine file size: {e}")
                # Assume it's valid and let other validations catch issues
                file_size = 0
        
        if file_size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            max_size_mb = self.app_settings.FILE_MAX_SIZE
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size / self.size_scale:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
            )
        
        return True
    
    def generate_unique_filepath(self, project_path: str, original_file_name: str):
        
        random_key = self.generate_random_string()
        cleaned_file_name = self.get_clean_file_name(orig_file_name=original_file_name)
        new_file_name = random_key + "_" + cleaned_file_name
        
        new_file_path = os.path.join(
            project_path, new_file_name
        )
        
        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path, random_key + "_" + cleaned_file_name
            )
        
        return new_file_path, new_file_name
        
   
    
    def get_clean_file_name(self, orig_file_name: str):
        
        # remove any special characters except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())
        
        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")
        
        return cleaned_file_name
    

        

        
        
    
        
