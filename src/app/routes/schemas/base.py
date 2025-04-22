from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Generic, TypeVar
from enum import Enum

T = TypeVar('T')

class BaseResponse(BaseModel):
    """Base response model for successful responses

    This model doesn't include any standard fields as successful responses
    should just return the requested data directly.
    """
    pass

class PaginatedResponse(Generic[T], BaseModel):
    """Base paginated response model"""
    items: List[T] = Field(..., description="List of items")
    page_number: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    total_items: int = Field(..., description="Total number of items")

class ErrorResponse(BaseModel):
    """Error response model

    This model is used for all error responses and includes:
    - type: A string identifying the type of error (replaces signal)
    - detail: A human-readable error message
    - errors: Optional list of validation errors
    """
    type: str = Field(..., description="Error type identifier")
    detail: str = Field(..., description="Error detail message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Validation errors if applicable")
