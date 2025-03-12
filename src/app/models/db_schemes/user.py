from pydantic import Field, EmailStr, BaseModel, field_validator
from typing import Optional
from odmantic import ObjectId
# from bson.objectid import ObjectId
from datetime import datetime, timezone


def datetime_now_sec():
    return datetime.now(timezone.utc).replace(microsecond=0)

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('username must be alphanumeric')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: Optional[ObjectId] = Field(None, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime_now_sec)
    is_active: bool = True
    
    class Config:
        arbitrary_types_allowed = True

class User(UserBase):
    id: Optional[ObjectId] = Field(None, alias="_id")
    is_active: bool = True
    
    class Config:
        arbitrary_types_allowed = True

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    jti: Optional[str] = None
    type: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None 