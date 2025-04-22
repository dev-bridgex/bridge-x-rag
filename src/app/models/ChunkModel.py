from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from typing import List, Optional, Tuple


class ChunkModel(BaseDataModel[DataChunk]):
    
    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name=None):
        super().__init__(db_client=db_client, collection_name=collection_name or DataBaseEnum.COLLECTION_CHUNK_NAME.value)
    
    def get_collection_name(self):
        return DataBaseEnum.COLLECTION_CHUNK_NAME.value
    
    def get_schema_model(self):
        return DataChunk
                
    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        """Create a new chunk using the base create method"""
        return await self.create(chunk)
    
    async def get_chunk(self, chunk_id: str) -> Optional[DataChunk]:
        """Get a chunk by ID"""
        return await self.find_one({"_id": ObjectId(chunk_id)})
    
    async def insert_many_chunks(self, chunks: List[DataChunk], batch_size: int=100) -> int:
        """Insert many chunks using the base create_many method"""
        return await self.create_many(chunks, batch_size=batch_size)
        
    async def delete_chunks_by_project_id(self, project_id: ObjectId) -> int:
        """Delete chunks by project ID using the base delete_many method"""
        return await self.delete_many({"chunk_project_id": project_id})
    
    async def delete_chunks_by_project_and_asset_id(self, project_id: ObjectId, asset_id: ObjectId) -> int:
        """Delete chunks by project ID and Assest ID using the base delete_many method"""
        return await self.delete_many({"chunk_project_id": project_id, "chunk_asset_id": asset_id})


    async def get_chunks_by_project_id(self, project_id: ObjectId, page: int = 1, page_size: int = 64) -> Tuple[List[DataChunk]]:
        """Get all chunks by Project ID using base find method"""   
        # calculate skip value
        skip = (page - 1) * page_size
        
        # get project chunks for the current page
        # Get projects for the current page
        chunks = await self.find_many({"chunk_project_id": project_id}, skip=skip, limit=page_size)
        
        return chunks
    
    async def get_chunks_count_by_project_id(self, project_id: ObjectId) -> int:
        """Get chunks count by project id"""
        
        chunks_count = await self.count_documents({"chunk_project_id": project_id})
        
        return chunks_count
        
        
    # async def get_chunks_by_project_id_with_pagination(self, project_id: ObjectId, page: int = 1, page_size: int = 64) -> Tuple[List[DataChunk], int]:
    #     """Get all chunks by Project ID using base find method"""   
    #     # calculate skip value
    #     skip = (page - 1) * page_size
        
    #     # count total documents for pagination
    #     total_documents = await self.count_documents({"chunk_project_id" : project_id})
        
    #     # calculate total pages
    #     total_pages = (total_documents + page_size - 1) // page_size
        
    #     # get project chunks for the current page
    #     # Get projects for the current page
    #     chunks = await self.find_many({"chunk_project_id": project_id}, skip=skip, limit=page_size)
        
    #     return chunks, total_pages
        