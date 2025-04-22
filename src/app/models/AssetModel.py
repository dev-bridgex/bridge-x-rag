from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional


class AssetModel(BaseDataModel[Asset]):
    
    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name=None):
        super().__init__(db_client=db_client, collection_name=collection_name or DataBaseEnum.COLLECTION_ASSET_NAME.value)
    
    def get_collection_name(self):
        return DataBaseEnum.COLLECTION_ASSET_NAME.value
    
    def get_schema_model(self):
        return Asset
                
    async def create_asset(self, asset: Asset) -> Asset:
        """Create a new asset using the base create method"""
        return await self.create(asset)
    
    
    async def get_asset_record(self, asset_project_id: str, asset_name: str) -> Optional[Asset]:
        """Get an asset by project ID and name"""
        project_id = ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id
        return await self.find_one({
            "asset_project_id": project_id,
            "asset_name": asset_name
        })
    
    
    async def get_all_project_assets(self, asset_project_id: str, asset_type: str | None = None) -> List[Asset]:
        """Get all assets for a project with a specific type"""
        project_id = ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id
        
        if asset_type is None:
            records =  await self.find_many({
                "asset_project_id": project_id,
            })
            
        else:
            records =  await self.find_many({
                "asset_project_id": project_id,
                "asset_type": asset_type
            })
        
        return records
