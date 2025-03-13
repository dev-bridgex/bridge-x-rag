from pydantic import BaseModel, Field, field_validator, ConfigDict
# from odmantic import ObjectId
from bson.objectid import ObjectId
from typing import Optional
# from datetime import datetime, timezone

class Project(BaseModel):
    id: Optional[ObjectId] | None = Field(alias="_id", default=None)
    project_id: str = Field(..., min_length=1)
    # created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    # updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    @field_validator('project_id')
    @classmethod
    def validator_project_id(cls, value):
        if not value.isalnum():
            raise ValueError('project_id must be alphanumeric')
        return value
    
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
        