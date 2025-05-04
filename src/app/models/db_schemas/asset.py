from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson.objectid import ObjectId
from datetime import datetime, timezone

class Asset(BaseModel):
    id: Optional[ObjectId] = Field(alias="_id", default=None)
    asset_knowledge_base_id: ObjectId
    asset_path: str = Field(..., min_length=1)
    asset_type: str = Field(..., min_length=1)
    asset_name: str = Field(..., min_length=1)
    asset_size: int = Field(gt=0, default=None)
    asset_config: dict = Field(default=None)
    asset_pushed_at: Optional[datetime] = None
    file_hash: str = Field(default="", description="Content hash of the file for deduplication")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def get_indexes(cls):

        return [
            {
                "key": [
                    ("asset_knowledge_base_id", 1)
                ],
                "name": "asset_knowledge_base_id_index_1",
                "unique": False
            },
            {
                "key": [
                    ("asset_knowledge_base_id", 1),
                    ("_id", 1)
                ],
                "name": "asset_knowledge_base_id_id_index_1",
                "unique": True
            }
        ]