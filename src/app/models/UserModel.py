from .BaseDataModel import BaseDataModel
from .db_schemes.user import UserInDB, User
from motor.motor_asyncio import AsyncIOMotorDatabase
from .enums.DataBaseEnum import DataBaseEnum
from datetime import datetime


def datetime_now_sec():
    return datetime.now().replace(microsecond=0)

class UserModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_USERS_NAME.value]
    
    async def get_user_by_username(self, username: str):
        user_doc = await self.collection.find_one({"username": username})
        if user_doc:
            return UserInDB(**user_doc)
        return None
    
    async def get_user_by_email(self, email: str):
        user_doc = await self.collection.find_one({"email": email})
        if user_doc:
            return UserInDB(**user_doc)
        return None
    
    async def create_user(self, username: str, email: str, hashed_password: str):
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime_now_sec(),
            "is_active": True
        }
        
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        return User(**user_data) 