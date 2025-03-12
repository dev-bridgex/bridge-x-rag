from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum

class ProjectModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
        
    
    async def create_project(self, project: Project):
        result = await self.collection.insert_one(project.model_dump(by_alias=True, exclude_unset=True))
        project.id = result.inserted_id
        
        return project
    
    
    async def get_project_or_create_one(self, project_id):
        record = await self.collection.find_one(
            {"project_id": project_id}
        )
        
        if record is None:
            # Create New Project
            new_project = Project(project_id=project_id)
            new_project = await self.create_project(project=new_project)
            
            return new_project
        
        return Project(**record)
    
    async def get_all_projects(self,page: int=1, page_size: int=10):
        
        # count total number of documents( projects )
        total_documents = await self.collection.count_documents({})
        
        # calculate total number of pages
        total_pages = total_documents // page_size
        if total_pages % page_size > 0:
            total_pages += 1 
        
        # fetch page records from database
        # using a cursor for memory effeciency to load the db documents (projects) one by one
        
        cursor = self.collection.find().skip( (page-1) * page_size ).limit(page_size)    
        
        projects = []
        async for document in cursor:
            projects.append(
                Project(**document)
            )

        return projects, total_pages