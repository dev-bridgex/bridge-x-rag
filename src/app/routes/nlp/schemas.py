from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Import the base response models from the central schemas
from app.routes.schemas.base import BaseResponse

class KnowledgeBaseIndexRequest(BaseModel):
    """Request model for indexing a knowledge base's chunks into vector database"""
    do_reset: Optional[bool] = Field(False, description="Whether to reset the collection and replace all existing vectors")
    skip_duplicates: Optional[bool] = Field(True, description="Whether to skip processing chunks that are already in the vector database (only applies when do_reset is False)")

class AssetIndexRequest(BaseModel):
    """Request model for indexing a specific asset into vector database"""
    do_reset: Optional[bool] = Field(False, description="Whether to delete and replace existing vectors for this asset")
    skip_duplicates: Optional[bool] = Field(True, description="Whether to skip processing chunks that are already in the vector database (only applies when do_reset is False)")

class SearchRequest(BaseModel):
    """Request model for searching in vector database"""
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(5, description="Maximum number of results to return")
    use_semantic: Optional[bool] = Field(True, description="Whether to use semantic search (vector search)")
    use_bm25: Optional[bool] = Field(False, description="Whether to use BM25 search (full-text search)")
    use_hybrid: Optional[bool] = Field(False, description="Whether to use hybrid search (combines semantic and BM25)")
    use_query_rewriting: Optional[bool] = Field(True, description="Whether to rewrite the query for better retrieval")


class ChatRequest(BaseModel):
    """Request model for chat with RAG"""
    query: str = Field(..., description="User query")
    history: List[Dict[str, str]] = Field([], description="Chat history")
    use_rag: Optional[bool] = Field(True, description="Whether to use RAG")
    use_hybrid: Optional[bool] = Field(True, description="Whether to use hybrid search (vector + text)")
    limit: Optional[int] = Field(5, description="Maximum number of chunks to retrieve")
    use_query_rewriting: Optional[bool] = Field(True, description="Whether to rewrite the query for better retrieval")

class IndexOperationResponse(BaseResponse):
    """Response model for indexing operation"""
    inserted_items_count: int = Field(..., description="Number of items inserted into the vector database")

class CollectionInfoResponse(BaseResponse):
    """Response model for collection info operation"""
    collection_info: Dict[str, Any] = Field(..., description="Information about the vector database collection")

class SearchResult(BaseModel):
    """Model for a single search result"""
    doc_num: str = Field(..., description="index of the search result")
    score: float = Field(..., description="Relevance score of the search result")
    text: str = Field(..., description="Text content of the search result")
    metadata: Dict[str, Any] = Field(..., description="Metadata associated with the search result")

class SearchResponse(BaseResponse):
    """Response model for search operation"""
    results: List[SearchResult] = Field(default_factory=list, description="List of search results")
    search_type: str = Field("semantic", description="Type of search that was performed (semantic, bm25, or hybrid)")
    message: Optional[str] = Field(None, description="Optional message, especially useful when no results are found")

class AssetIndexResponse(BaseResponse):
    """Response model for asset indexing operation"""
    asset_id: str = Field(..., description="ID of the indexed asset")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base the asset belongs to")
    indexed_chunks_count: int = Field(..., description="Number of chunks indexed for this asset")

class AssetDeleteResponse(BaseResponse):
    """Response model for asset deletion from vector database operation"""
    asset_id: str = Field(..., description="ID of the deleted asset")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base the asset belongs to")
    deleted_from_vector_db: bool = Field(..., description="Whether the asset was successfully deleted from vector database")

class ChatResponse(BaseResponse):
    """Response model for chat operation"""
    query: str = Field(..., description="Original query")
    response: str = Field(..., description="Generated response text")
    sources: List[SearchResult] = Field([], description="List of sources used to generate the response")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base used for the chat")


