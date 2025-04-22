from pydantic import BaseModel, Field, field_validator, ConfigDict
from bson.objectid import ObjectId
from typing import Optional
from datetime import datetime, timezone

class KnowledgeBase(BaseModel):
    id: Optional[ObjectId] | None = Field(alias="_id", default=None)
    knowledge_base_name: str = Field(..., min_length=1, description="Unique name for the knowledge base")
    knowledge_base_dir_path: str = Field(default="")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('knowledge_base_name')
    @classmethod
    def validator_knowledge_base_name(cls, value: str):
        # Validate that the name is not None
        if value is None:
            raise ValueError('knowledge_base_name cannot be None')

        # Validate that the name contains only ASCII characters
        if not value.isascii():
            raise ValueError('knowledge_base_name must contain ASCII characters only')

        # Validate that the name is not empty or just whitespace
        if not value.strip():
            raise ValueError('knowledge_base_name cannot be empty or just whitespace')

        # Check for invalid characters (common filesystem restrictions)
        # Only truly problematic filesystem characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in value for char in invalid_chars):
            raise ValueError(f"knowledge_base_name contains invalid characters. The following characters are not allowed: {', '.join(invalid_chars)}")

        # Standardize the name to lowercase
        return value.lower()


    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("knowledge_base_name", 1)  # 1 ==> ascending index, -1 ==> desc index
                ],
                "name": "knowledge_base_name_index_1",
                "unique": True
            }
        ]
