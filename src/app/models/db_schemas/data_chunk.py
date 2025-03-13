from pydantic import BaseModel, Field
from typing import Optional
# from odmantic import ObjectId
from bson.objectid import ObjectId


class DataChunk(BaseModel):
    id: Optional[ObjectId] | None = Field(default=None, alias='_id')
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: ObjectId
    
    class Config:
        arbitrary_types_allowed = True
