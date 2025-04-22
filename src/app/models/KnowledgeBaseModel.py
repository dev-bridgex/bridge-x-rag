from .BaseDataModel import BaseDataModel
from app.models.db_schemas import KnowledgeBase
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from typing import List, Tuple, Optional, Dict, Any
from bson.objectid import ObjectId
from app.logging import get_logger
from datetime import datetime, timezone
from copy import deepcopy

logger = get_logger(__name__)

class KnowledgeBaseModel(BaseDataModel[KnowledgeBase]):
    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name=None):
        super().__init__(db_client=db_client, collection_name=collection_name or DataBaseEnum.COLLECTION_KNOWLEDGE_BASE_NAME.value)
        self.asset_model = None
        self.chunk_model = None

    async def _init_related_models(self):
        """Initialize related models if they haven't been initialized yet"""
        if self.asset_model is None or self.chunk_model is None:
            from app.models import AssetModel, ChunkModel
            self.asset_model = await AssetModel.create_instance(db_client=self.db_client)
            self.chunk_model = await ChunkModel.create_instance(db_client=self.db_client)


    def get_collection_name(self):
        return DataBaseEnum.COLLECTION_KNOWLEDGE_BASE_NAME.value

    def get_schema_model(self):
        return KnowledgeBase

    async def create(self, model_instance):
        """Create a new knowledge base with proper timestamps

        Args:
            model_instance: The knowledge base to create

        Returns:
            The created knowledge base
        """
        # Make a copy to avoid modifying the original
        model_copy = deepcopy(model_instance)

        # Set timestamps for new records
        now = datetime.now(timezone.utc)
        model_copy.created_at = now
        model_copy.updated_at = now

        # Use the base create method
        return await super().create(model_copy)

    async def get_knowledge_base_by_id(self, knowledge_base_id) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID

        Args:
            knowledge_base_id: The ID of the knowledge base (string or ObjectId)

        Returns:
            The knowledge base if found, None otherwise
        """
        try:
            # Convert string ID to ObjectId if needed
            kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
            return await self.find_one({"_id": kb_id})
        except Exception as e:
            logger.debug(f"Error getting knowledge base by ID: {e}")
            return None

    async def get_knowledge_base_by_name(self, knowledge_base_name: str) -> Optional[KnowledgeBase]:
        """Search for a knowledge base by name

        Args:
            knowledge_base_name: The name of the knowledge base to search for

        Returns:
            The knowledge base if found, None otherwise
        """
        return await self.find_one({"knowledge_base_name": knowledge_base_name})

    async def get_all_knowledge_bases(self, page: int=1, page_size: int=10, sort: Optional[List[tuple]] = None) -> Tuple[List[KnowledgeBase], int, int]:
        """Get all knowledge bases with pagination

        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            sort: Optional list of (field, direction) tuples for sorting

        Returns:
            Tuple of (knowledge_bases, total_pages, total_items)
        """
        try:
            # Use the paginate method from BaseDataModel
            return await self.paginate(
                filter_dict={},
                page=page,
                page_size=page_size,
                sort=sort
            )
        except Exception as e:
            logger.error(f"Error getting all knowledge bases: {e}")
            return [], 0, 0


    async def update_knowledge_base_data(self, knowledge_base_id, update_data: Dict[str, Any]) -> Tuple[bool, Optional[KnowledgeBase]]:
        """Update a knowledge base's data in MongoDB

        Args:
            knowledge_base_id: The ID of the knowledge base to update
            update_data: Dictionary of fields to update

        Returns:
            Tuple of (success, updated_knowledge_base)
        """
        # Always update the updated_at timestamp on explicit updates
        # But never update the created_at timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)

        # Ensure we never update the created_at field
        if "created_at" in update_data:
            del update_data["created_at"]

        try:
            # Convert string ID to ObjectId if needed
            kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id

            # Update knowledge base in database
            success = await self.update_one(
                filter_dict={"_id": kb_id},
                update_dict=update_data
            )
        except Exception as e:
            logger.error(f"Error updating knowledge base data: {e}")
            return False, None

        if not success:
            return False, None

        # Get updated knowledge base
        updated_knowledge_base = await self.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
        return True, updated_knowledge_base

    async def delete_knowledge_base_cascade(self, knowledge_base_id) -> Tuple[bool, int, int]:
        """Delete a knowledge base and all its related resources in MongoDB"""
        # Get knowledge base by ID
        knowledge_base = await self.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
        if knowledge_base is None:
            return False, 0, 0

        # Initialize related models
        await self._init_related_models()

        # Delete knowledge base assets from database
        assets_deleted = await self.asset_model.delete_many({"asset_knowledge_base_id": knowledge_base.id})
        logger.info(f"Deleted {assets_deleted} assets for knowledge base ID '{knowledge_base_id}'")

        # Delete knowledge base chunks from database
        chunks_deleted = await self.chunk_model.delete_chunks_by_knowledge_base_id(knowledge_base_id=knowledge_base.id)
        logger.info(f"Deleted {chunks_deleted} chunks for knowledge base ID '{knowledge_base_id}'")

        # Delete knowledge base from database
        knowledge_base_deleted = await self.delete_one({"_id": knowledge_base.id})

        return knowledge_base_deleted, assets_deleted, chunks_deleted
