from pydantic import BaseModel, Field, field_validator, ConfigDict
# from odmantic import ObjectId
from bson.objectid import ObjectId
from typing import Optional
from datetime import datetime, timezone

class Project(BaseModel):
    id: Optional[ObjectId] | None = Field(alias="_id", default=None)
    project_name: str = Field(..., min_length=1)
    project_dir_path: str = Field(..., min_length=1)
    created_at: datetime = Field(...)
    updated_at: datetime = Field( default=datetime.now(timezone.utc) )
       
    @field_validator('project_name')
    @classmethod
    def validator_project_id(cls, value: str):
        if not value.isascii():
            raise ValueError('project_name must contain ascii characters only')
        return value
    
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @classmethod
    def get_indexes(cls):
        
        return [
            {
                "key": [
                    ("project_name", 1) # 1 ==> ascending index, -1 ==> desc index
                ],
                "name": "project_name_index_1",
                "unique": True
            }
        ]