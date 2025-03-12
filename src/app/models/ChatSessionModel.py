from .BaseDataModel import BaseDataModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from datetime import datetime, timedelta, timezone
import secrets
import string

class ChatSessionModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHAT_SESSIONS_NAME.value]
    
    def generate_session_token(self, length=32):
        """Generate a secure random session token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def create_session(self, user_id: str, project_id: str, expires_in_minutes: int = 60):
        """Create a new chat session with a short-lived token"""
        session_token = self.generate_session_token()
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=expires_in_minutes)
        
        session_data = {
            "user_id": user_id,
            "project_id": project_id,
            "token": session_token,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "expires_at": expires_at,
            "is_active": True,
            "last_used": datetime.now(timezone.utc).replace(tzinfo=None)
        }
        
        result = await self.collection.insert_one(session_data)
        session_data["_id"] = result.inserted_id
        
        return {
            "session_token": session_token,
            "expires_at": expires_at
        }
    
    async def validate_session_token(self, token: str):
        """Validate a session token and update last_used timestamp"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session = await self.collection.find_one({
            "token": token, 
            "is_active": True,
            "expires_at": {"$gt": now}
        })
        
        if session:
            # Update last used timestamp
            await self.collection.update_one(
                {"_id": session["_id"]},
                {"$set": {"last_used": now}}
            )
            return {
                "valid": True,
                "user_id": session["user_id"],
                "project_id": session["project_id"]
            }
        return {"valid": False}
    
    async def revoke_session(self, token: str):
        """Revoke a session token"""
        result = await self.collection.update_one(
            {"token": token},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions from the database"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self.collection.delete_many({
            "expires_at": {"$lt": now}
        })
        return result.deleted_count 