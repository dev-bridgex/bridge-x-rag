from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Tuple
from app.logging import get_logger
from datetime import datetime, timezone
from copy import deepcopy

logger = get_logger(__name__)

class AssetModel(BaseDataModel[Asset]):

    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name=None):
        super().__init__(db_client=db_client, collection_name=collection_name or DataBaseEnum.COLLECTION_ASSET_NAME.value)
        self.chunk_model = None

    def get_collection_name(self):
        return DataBaseEnum.COLLECTION_ASSET_NAME.value

    def get_schema_model(self):
        return Asset

    async def _init_related_models(self):
        """Initialize related models if they haven't been initialized yet"""
        if self.chunk_model is None:
            from app.models import ChunkModel
            self.chunk_model = await ChunkModel.create_instance(db_client=self.db_client)

    async def create(self, model_instance):
        """Create a new asset with proper timestamp

        Args:
            model_instance: The asset to create

        Returns:
            The created asset
        """
        # Make a copy to avoid modifying the original
        model_copy = deepcopy(model_instance)

        # Set timestamp for new records
        model_copy.asset_pushed_at = datetime.now(timezone.utc)

        # Use the base create method
        return await super().create(model_copy)

    async def get_asset_by_id(self, asset_id) -> Optional[Asset]:
        """Get an asset by ID

        Args:
            asset_id: The ID of the asset (string or ObjectId)

        Returns:
            The asset if found, None otherwise
        """
        try:
            # Convert string ID to ObjectId if needed
            a_id = ObjectId(asset_id) if isinstance(asset_id, str) else asset_id
            return await self.find_one({"_id": a_id})
        except Exception as e:
            logger.debug(f"Error getting asset by ID: {e}")
            return None

    async def get_asset_by_knowledge_base_and_name(self, knowledge_base_id, asset_name: str) -> Optional[Asset]:
        """Get an asset by knowledge base ID and name

        Args:
            knowledge_base_id: The ID of the knowledge base (string or ObjectId)
            asset_name: The name of the asset

        Returns:
            The asset if found, None otherwise
        """
        try:
            # Convert string ID to ObjectId if needed
            kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id
            return await self.find_one({
                "asset_knowledge_base_id": kb_id,
                "asset_name": asset_name
            })
        except Exception as e:
            logger.debug(f"Error getting asset by knowledge base and name: {e}")
            return None

    async def get_all_knowledge_base_assets(self, knowledge_base_id, asset_type: str | None = None,
                                page: int = 1, page_size: int = 10,
                                sort: List[tuple] = None) -> Tuple[List[Asset], int, int]:
        """Get all assets for a knowledge base with a specific type, with pagination support

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_type: Optional filter for asset type
            page: Page number (1-based)
            page_size: Number of items per page
            sort: List of (field, direction) tuples for sorting

        Returns:
            Tuple of (assets, total_pages, total_items)
        """
        try:
            # Convert string ID to ObjectId if needed
            kb_id = ObjectId(knowledge_base_id) if isinstance(knowledge_base_id, str) else knowledge_base_id

            # Default sort by upload date (newest first) if not specified
            if sort is None:
                sort = [("asset_pushed_at", -1)]

            # Create filter dict based on parameters
            filter_dict = {"asset_knowledge_base_id": kb_id}
            if asset_type is not None:
                filter_dict["asset_type"] = asset_type

            # Use the paginate method from BaseDataModel
            return await self.paginate(
                filter_dict=filter_dict,
                page=page,
                page_size=page_size,
                sort=sort
            )
        except Exception as e:
            logger.error(f"Error getting knowledge base assets: {e}")
            return [], 0, 0



    async def update_asset_data(self, asset_id, update_data) -> Tuple[bool, Optional[Asset]]:
        """Update an asset's data in MongoDB

        Args:
            asset_id: The ID of the asset to update (string or ObjectId)
            update_data: Dictionary of fields to update

        Returns:
            Tuple of (success, updated_asset)
        """
        # Always update the asset_pushed_at timestamp on explicit updates
        update_data["asset_pushed_at"] = datetime.now(timezone.utc)

        try:
            # Convert string ID to ObjectId if needed
            a_id = ObjectId(asset_id) if isinstance(asset_id, str) else asset_id

            # Update asset in database
            success = await self.update_one(
                filter_dict={"_id": a_id},
                update_dict=update_data
            )
        except Exception as e:
            logger.error(f"Error updating asset data: {e}")
            return False, None

        if not success:
            return False, None

        # Get updated asset
        updated_asset = await self.get_asset_by_id(asset_id=asset_id)
        return True, updated_asset

    async def delete_asset_cascade(self, asset_id) -> Tuple[bool, int]:
        """Delete an asset and all its related resources (chunks)"""
        # Get asset by ID
        asset = await self.get_asset_by_id(asset_id=asset_id)
        if asset is None:
            return False, 0

        # Initialize related models
        await self._init_related_models()

        # Delete chunks using knowledge_base_id
        chunks_deleted = await self.chunk_model.delete_chunks_by_knowledge_base_and_asset_id(
            knowledge_base_id=asset.asset_knowledge_base_id,
            asset_id=asset.id
        )
        logger.info(f"Deleted {chunks_deleted} chunks for asset ID '{asset_id}' with knowledge_base_id '{asset.asset_knowledge_base_id}'")

        # Delete asset from database
        asset_deleted = await self.delete_one({"_id": asset.id})

        return asset_deleted, chunks_deleted
