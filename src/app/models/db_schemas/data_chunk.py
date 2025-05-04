from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from bson.objectid import ObjectId


class DataChunk(BaseModel):
    id: Optional[ObjectId] | None = Field(default=None, alias='_id')
    chunk_text: str = Field(..., min_length=1)
    chunk_order: int = Field(..., gt=0)
    chunk_knowledge_base_id: ObjectId
    chunk_asset_id: ObjectId

    # Store all metadata in a single field
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("chunk_knowledge_base_id", 1)
                ],
                "name": "chunk_knowledge_base_id_index_1",
                "unique": False
            },
            {
                "key": [
                    ("chunk_knowledge_base_id", 1),
                    ("chunk_asset_id", 1)
                ],
                "name": "chunk_knowledge_base_id_asset_id_index_1",
                "unique": False
            },
            {
                "key": [
                    ("chunk_text", "text")
                ],
                "name": "chunk_text_index",
                "unique": False
            },
        ]


class RetrievedDocument(BaseModel):
    """
    Model for documents retrieved from the vector database.

    This model represents the structure of documents returned from vector search operations.
    It includes the document text, relevance score, and all associated metadata.
    """
    score: float
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the retrieved document")
