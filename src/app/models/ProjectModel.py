from .BaseDataModel import BaseDataModel
from app.models.db_schemas import Project
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from typing import List, Tuple

class ProjectModel(BaseDataModel[Project]):
    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name=None):
        super().__init__(db_client=db_client, collection_name=collection_name or DataBaseEnum.COLLECTION_PROJECT_NAME.value)
    
    def get_collection_name(self):
        return DataBaseEnum.COLLECTION_PROJECT_NAME.value
    
    def get_schema_model(self):
        return Project

    async def create_project(self, project: Project):
        """Create a new Project """
        return await self.create(project)
    
    async def get_project_by_name(self, project_name: str):
        """Search for a project by name"""
        return await self.find_one({"project_name": project_name})
    
    async def get_all_projects(self, page: int=1, page_size: int=10) -> Tuple[List[Project], int]:
        """Get all projects with pagination"""
        # Calculate skip value
        skip = (page - 1) * page_size
        
        # Count total documents for pagination
        total_documents = await self.count_documents({})
        
        # Calculate total pages
        total_pages = (total_documents + page_size - 1) // page_size
        
        # Get projects for the current page
        projects = await self.find_many({}, skip=skip, limit=page_size)
        
        return projects, total_pages