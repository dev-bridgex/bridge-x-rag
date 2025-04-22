from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from app.utils.datetime_utils import format_datetime


# Import the base response models from the central schemas
from app.routes.schemas.base import BaseResponse, PaginatedResponse


class AssetBase(BaseModel):
    """Base schema for asset"""
    name: str
    type: str
    size: int = Field(..., description="Asset size in bytes, displayed as megabytes in responses")

    @field_serializer('size')
    def serialize_size(self, size: int) -> float:
        """Convert size from bytes to megabytes"""
        return round(size / (1024 * 1024), 4)  # Convert bytes to MB with 2 decimal places


class AssetCreate(BaseModel):
    """Schema for creating a new asset"""
    knowledge_base_id: str
    # File will be handled by UploadFile


class AssetResponse(AssetBase):
    """Schema for asset response"""
    id: str
    path: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    knowledge_base_id: str
    knowledge_base_name: str

    @field_serializer('uploaded_at')
    def serialize_datetime(self, dt: datetime) -> str:
        if dt is None:
            return None
        # Format in Egypt timezone by default
        return format_datetime(dt, tz_name='Africa/Cairo')


class AssetListItem(AssetBase):
    """Schema for asset list item"""
    id: str
    uploaded_at: Optional[datetime] = None

    @field_serializer('uploaded_at')
    def serialize_datetime(self, dt: datetime) -> str:
        if dt is None:
            return None
        # Format in Egypt timezone by default
        return format_datetime(dt, tz_name='Africa/Cairo')



class PaginatedAssetListResponse(BaseResponse, PaginatedResponse[AssetListItem]):
    """Schema for paginated asset list response"""
    knowledge_base_id: str
    knowledge_base_name: str
    items: List[AssetListItem] = Field(..., alias="assets")


class AssetDetailResponse(BaseResponse):
    """Schema for detailed asset response"""
    asset: AssetResponse


class AssetCreateResponse(BaseResponse):
    """Schema for asset creation response"""
    asset_id: str
    asset_name: str
    knowledge_base_id: str
    knowledge_base_name: str


class AssetDeleteResponse(BaseResponse):
    """Schema for asset deletion response

    This schema defines the response format for asset deletion operations.
    It provides information about the deleted asset and the status of various deletion operations.
    """
    asset_id: str = Field(..., description="ID of the deleted asset")
    asset_name: str = Field(..., description="Name of the deleted asset")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base the asset belonged to")
    knowledge_base_name: str = Field(..., description="Name of the knowledge base the asset belonged to")
    file_deleted: bool = Field(..., description="Whether the asset file was successfully deleted from disk")
    chunks_deleted: int = Field(..., description="Number of chunks deleted from the database")
    vector_db_deleted: bool = Field(False, description="Whether the asset was successfully deleted from vector database")



class KnowledgeBaseProcessRequest(BaseModel):
    """Schema for knowledge-base-wide asset processing request

    This schema defines the parameters for processing all assets in a knowledge base into chunks for RAG operations.
    It controls how documents are split, how much context is preserved between chunks,
    and whether existing chunks should be replaced.
    """
    chunk_size: Optional[int] = Field(
        default=500,
        gt=0,
        le=1000,
        description="Size of text chunks in characters. Larger chunks provide more context but may reduce relevance precision. "
                    "Recommended values: 300-1000 for short documents, 600-1500 for longer documents.",
        example=500
    )

    overlap_size: Optional[int] = Field(
        default=50,
        ge=0,
        le=200,
        description="Overlap between chunks in characters. Higher overlap preserves context between chunks but increases "
                    "storage requirements. Typically 10-20% of chunk_size is recommended.",
        example=50
    )

    do_reset: Optional[bool] = Field(
        default=False,
        description="Whether to delete and replace existing chunks. Set to true to reprocess assets that have already "
                    "been processed, or false to keep existing chunks and only process new assets.",
        example=False
    )

    reset_vector_db: Optional[bool] = Field(
        default=False,
        description="Whether to also reset the vector database entries. If not specified (None), follows the do_reset value.",
        example=False
    )

    skip_duplicates: Optional[bool] = Field(
        default=True,
        description="Whether to skip processing assets that already have chunks. Only applies when do_reset is False."
    )

    batch_size: Optional[int] = Field(
        default=50,
        gt=0,
        le=100,
        description="Number of assets to process in each batch. Higher values process more assets at once but may use more memory.",
        example=50
    )

    class Config:
        schema_extra = {
            "example": {
                "chunk_size": 500,
                "overlap_size": 50,
                "do_reset": False,
                "reset_vector_db": False,
                "skip_duplicates": True,
                "batch_size": 50
            }
        }


class AssetProcessRequest(BaseModel):
    """Schema for single asset processing request

    This schema defines the parameters for processing a specific asset into chunks for RAG operations.
    It controls how the document is split, how much context is preserved between chunks,
    and whether existing chunks should be replaced.
    """
    chunk_size: Optional[int] = Field(
        default=500,
        gt=0,
        le=1000,
        description="Size of text chunks in characters. Larger chunks provide more context but may reduce relevance precision. "
                    "Recommended values: 300-1000 for short documents, 600-1500 for longer documents.",
        example=500
    )

    overlap_size: Optional[int] = Field(
        default=50,
        ge=0,
        le=500,
        description="Overlap between chunks in characters. Higher overlap preserves context between chunks but increases "
                    "storage requirements. Typically 10-20% of chunk_size is recommended.",
        example=50
    )

    do_reset: Optional[bool] = Field(
        default=False,
        description="Whether to delete and replace existing chunks. Set to true to reprocess the asset if it has already "
                    "been processed, or false to keep existing chunks.",
        example=False
    )

    reset_vector_db: Optional[bool] = Field(
        default=False,
        description="Whether to also reset the vector database entries. If not specified (None), follows the do_reset value.",
        example=False
    )

    skip_duplicates: Optional[bool] = Field(
        default=True,
        description="Whether to skip processing if the asset already has chunks. Only applies when do_reset is False."
    )

    class Config:
        schema_extra = {
            "example": {
                "chunk_size": 500,
                "overlap_size": 50,
                "do_reset": False,
                "reset_vector_db": False,
                "skip_duplicates": True
            }
        }


class AssetProcessResponse(BaseResponse):
    """Schema for asset processing response

    This schema defines the response format for asset processing operations.
    It provides information about how many files were processed and how many
    chunks were created during the processing operation.
    """
    processed_files: int = Field(
        description="Number of files successfully processed during the operation",
        example=1,
        ge=0
    )

    inserted_chunks: int = Field(
        description="Total number of text chunks created and inserted into the database",
        example=42,
        ge=0
    )

    total_assets: Optional[int] = Field(
        None,
        description="Total number of assets in the knowledge base (only for batch processing)",
        example=100,
        ge=0
    )

    class Config:
        schema_extra = {
            "example": {
                "processed_files": 1,
                "inserted_chunks": 42,
                "total_assets": 100
            }
        }
