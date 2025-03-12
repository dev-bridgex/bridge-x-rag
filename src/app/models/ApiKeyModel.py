from .BaseDataModel import BaseDataModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from datetime import datetime, timezone
import secrets
import string
from bson.objectid import ObjectId

class ApiKeyModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_API_KEYS_NAME.value]
    
    def generate_api_key(self, length=32):
        """Generate a secure random API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def create_api_key(self, name: str, description: str = None):
        """Create a new API key"""
        api_key = self.generate_api_key()
        key_data = {
            "name": name,
            "description": description,
            "key": api_key,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "is_active": True,
            "last_used": None
        }
        
        result = await self.collection.insert_one(key_data)
        key_data["_id"] = result.inserted_id
        
        return key_data
    
    async def validate_api_key(self, api_key: str):
        """Validate an API key and update last_used timestamp"""
        key_doc = await self.collection.find_one({"key": api_key, "is_active": True})
        if key_doc:
            # Update last used timestamp
            await self.collection.update_one(
                {"_id": key_doc["_id"]},
                {"$set": {"last_used": datetime.now(timezone.utc).replace(tzinfo=None)}}
            )
            return True
        return False
    
    async def revoke_api_key(self, api_key: str):
        """Revoke an API key"""
        result = await self.collection.update_one(
            {"key": api_key},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    async def get_api_keys(self, skip: int = 0, limit: int = 100):
        """Get a list of API keys (for admin UI)"""
        cursor = self.collection.find().skip(skip).limit(limit)
        keys = []
        async for key in cursor:
            # Don't return the actual key value in listings for security
            key_info = {
                "id": str(key["_id"]),
                "name": key["name"],
                "description": key["description"],
                "created_at": key["created_at"],
                "is_active": key["is_active"],
                "last_used": key["last_used"]
            }
            keys.append(key_info)
        return keys
    
    async def get_api_key_by_id(self, key_id: str):
        """Get API key details by ID"""
        try:
            key = await self.collection.find_one({"_id": ObjectId(key_id)})
            if key:
                return {
                    "id": str(key["_id"]),
                    "name": key["name"],
                    "description": key["description"],
                    "key": key["key"],  # Include actual key value when requested directly
                    "created_at": key["created_at"],
                    "is_active": key["is_active"],
                    "last_used": key["last_used"]
                }
        except Exception:
            return None
        return None 