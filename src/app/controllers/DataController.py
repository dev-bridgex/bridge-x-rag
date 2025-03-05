from fastapi import UploadFile
from .BaseController import BaseController
from models import ResponseSignal
import re
import os

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 # Convert MB to Bytes
        
    def validate_uploaded_file(self, file: UploadFile):
        
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value
        
        return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value
    
    def generate_unique_filepath(self, project_path: str, original_file_name: str):
        
        random_key = self.generate_random_string()
        cleaned_file_name = self.get_clean_file_name(orig_file_name=original_file_name)
        
        new_file_path = os.path.join(
            project_path, random_key + "_" + cleaned_file_name
        )
        
        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path, random_key + "_" + cleaned_file_name
            )
        
        return new_file_path, random_key + "_" + cleaned_file_name
        
   
    
    def get_clean_file_name(self, orig_file_name: str):
        
        # remove any special characters except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())
        
        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")
        
        return cleaned_file_name
    

        

        
        
    
        
