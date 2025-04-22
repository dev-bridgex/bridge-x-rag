from .BaseController import BaseController
import os

class ProjectController(BaseController):
    def __init__(self):
        super().__init__()
    
    
    def get_project_path(self, project_name: str):
        project_dir_path = os.path.join( self.files_dir, project_name )
        
        if not os.path.exists(project_dir_path):
            os.mkdir(project_dir_path)
        
        return project_dir_path
    
    
    def find_project_path(self, project_name: str):
        project_dir_path = os.path.join( self.files_dir, project_name)
        
        if not os.path.exists(project_dir_path):
            return None
        
        return project_dir_path
        
        
    
    