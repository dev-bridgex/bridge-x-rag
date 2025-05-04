from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .db_schemas.data_chunk import RetrievedDocument
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from typing import List, Optional, Dict, Any
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



    async def search_text(self, knowledge_base_id: str, query: str, limit: int = 10) -> List[RetrievedDocument]:
        """
        Perform full-text search using MongoDB's text search capabilities

        Args:
            knowledge_base_id: ID of the knowledge base to search in
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of RetrievedDocument objects
        """
        try:
            # Convert string ID to ObjectId if needed
            kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id

            # Clean and prepare the query
            clean_query = query.strip()

            # Log the search attempt
            logger.debug(f"Performing MongoDB text search with query: '{clean_query}'")

            # Perform text search in MongoDB with improved options
            pipeline = [
                {
                    "$match": {
                        "$and": [
                            {"chunk_knowledge_base_id": kb_id},
                            {"$text": {
                                "$search": clean_query,
                                "$caseSensitive": False,
                                "$diacriticSensitive": False
                            }}
                        ]
                    }
                },
                {
                    "$project": {
                        "chunk_text": 1,
                        "metadata": 1,
                        "chunk_asset_id": 1,
                        "chunk_order": 1,
                        "score": {"$meta": "textScore"}
                    }
                },
                {"$sort": {"score": -1}},
                {"$limit": limit}
            ]

            cursor = self.collection.aggregate(pipeline)

            # Convert MongoDB documents to RetrievedDocument objects
            retrieved_docs = []
            async for doc in cursor:
                # Create metadata dictionary
                metadata = {
                    "id": str(doc.get("_id")),
                    "asset_id": str(doc.get("chunk_asset_id", "")),
                    "knowledge_base_id": str(knowledge_base_id),
                    "chunk_order": doc.get("chunk_order", 0)
                }

                # Add any existing metadata from the document's metadata field
                if "metadata" in doc and isinstance(doc["metadata"], dict):
                    metadata.update(doc["metadata"])

                retrieved_docs.append(RetrievedDocument(
                    text=doc.get("chunk_text", ""),
                    metadata=metadata,
                    score=doc.get("score", 0.0)
                ))

            # Log the results
            if retrieved_docs:
                logger.info(f"MongoDB text search found {len(retrieved_docs)} documents for query: '{clean_query}'")
            else:
                logger.warning(f"MongoDB text search found no results for query: '{clean_query}'")

            return retrieved_docs
        except Exception as e:
            logger.error(f"Error performing MongoDB text search: {str(e)}")
            return []