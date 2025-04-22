from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from typing import List, Optional
from app.logging import get_logger

logger = get_logger(__name__)

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

    async def delete_chunks_by_knowledge_base_id(self, knowledge_base_id) -> int:
        """Delete chunks by knowledge base ID using the base delete_many method

        Args:
            knowledge_base_id: The knowledge base ID (string or ObjectId)

        Returns:
            Number of chunks deleted
        """
        # Convert string ID to ObjectId if needed
        kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
        return await self.delete_many({"chunk_knowledge_base_id": kb_id})

    async def delete_chunks_by_knowledge_base_and_asset_id(self, knowledge_base_id, asset_id) -> int:
        """Delete chunks by knowledge base ID and Asset ID using the base delete_many method

        Args:
            knowledge_base_id: The knowledge base ID (string or ObjectId)
            asset_id: The asset ID (string or ObjectId)

        Returns:
            Number of chunks deleted
        """
        # Convert string IDs to ObjectId if needed
        kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
        a_id = ObjectId(asset_id) if isinstance(asset_id, str) else asset_id
        return await self.delete_many({"chunk_knowledge_base_id": kb_id, "chunk_asset_id": a_id})

    async def get_chunks_by_knowledge_base_id(self, knowledge_base_id, page: int = 1, page_size: int = 64) -> List[DataChunk]:
        """Get all chunks by Knowledge Base ID using base find method

        Args:
            knowledge_base_id: The knowledge base ID (string or ObjectId)
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            List of chunks for the knowledge base
        """
        # Convert string ID to ObjectId if needed
        kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id

        # calculate skip value
        skip = (page - 1) * page_size

        # get knowledge base chunks for the current page
        chunks = await self.find_many({"chunk_knowledge_base_id": kb_id}, skip=skip, limit=page_size)

        return chunks

    async def get_chunks_by_knowledge_base_and_asset_id(self, knowledge_base_id: ObjectId, asset_id: ObjectId) -> List[DataChunk]:
        """Get all chunks by Knowledge Base ID and Asset ID"""
        # Convert string IDs to ObjectId if needed
        kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
        a_id = ObjectId(asset_id) if isinstance(asset_id, str) else asset_id

        # Get chunks matching both knowledge base and asset IDs
        chunks = await self.find_many({
            "chunk_knowledge_base_id": kb_id,
            "chunk_asset_id": a_id
        })

        return chunks

    async def get_chunks_count_by_knowledge_base_id(self, knowledge_base_id) -> int:
        """Get chunks count by knowledge base id

        Args:
            knowledge_base_id: The knowledge base ID (string or ObjectId)

        Returns:
            Number of chunks for the knowledge base
        """
        # Convert string ID to ObjectId if needed
        kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
        chunks_count = await self.count_documents({"chunk_knowledge_base_id": kb_id})

        return chunks_count