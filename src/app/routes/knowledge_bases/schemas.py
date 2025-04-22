from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from app.utils.datetime_utils import format_datetime


# Import the base response models from the central schemas
from app.routes.schemas.base import BaseResponse, PaginatedResponse


class KnowledgeBaseBase(BaseModel):
    """Base schema for knowledge base"""
    knowledge_base_name: str = Field(
        ...,
        min_length=3,
        description="Name of the knowledge base. Must not be empty and contain only valid characters."
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Schema for creating a new knowledge base"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base"""
    knowledge_base_name: Optional[str] = Field(
        None,
        min_length=1,
        description="New name for the knowledge base. Must not be empty and contain only valid characters."
    )


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """Schema for knowledge base response"""
    id: str
    knowledge_base_dir_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        if dt is None:
            return None
        # Format in Egypt timezone by default
        return format_datetime(dt, tz_name='Africa/Cairo')


class KnowledgeBaseListItem(KnowledgeBaseBase):
    """Schema for knowledge base list item"""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        if dt is None:
            return None
        # Format in Egypt timezone by default
        return format_datetime(dt, tz_name='Africa/Cairo')


class PaginatedKnowledgeBaseListResponse(BaseResponse, PaginatedResponse[KnowledgeBaseListItem]):
    """Schema for knowledge base list response"""
    items: List[KnowledgeBaseListItem] = Field(..., alias="knowledge_bases")


class KnowledgeBaseDetailResponse(BaseResponse):
    """Schema for detailed knowledge base response"""
    knowledge_base: KnowledgeBaseResponse


class KnowledgeBaseCreateResponse(BaseResponse):
    """Schema for knowledge base creation response"""
    knowledge_base_id: str
    knowledge_base_name: str


class KnowledgeBaseUpdateResponse(BaseResponse):
    """Schema for knowledge base update response"""
    knowledge_base_id: str
    knowledge_base_name: str
    resources_updated: bool


class KnowledgeBaseDeleteResponse(BaseResponse):
    """Schema for knowledge base deletion response"""
    knowledge_base_id: str
    knowledge_base_name: str
    resources_deleted: bool
    vector_db_deleted: bool
    directory_deleted: bool
    assets_deleted: int
    chunks_deleted: int
