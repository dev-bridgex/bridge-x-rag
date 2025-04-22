from enum import Enum

class ErrorType(str, Enum):
    """Error types for API responses

    This enum replaces the ResponseSignalEnum and is used only for error responses.
    It provides a standardized set of error types that can be used across the API.
    """
    # General errors
    VALIDATION_ERROR = "validation_error"
    INVALID_REQUEST = "invalid_request"
    RESOURCE_CONFLICT = "resource_conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Knowledge base errors
    KNOWLEDGE_BASE_NOT_FOUND = "knowledge_base_not_found"

    # Asset errors
    ASSET_NOT_FOUND = "asset_not_found"
    FILE_NOT_FOUND = "file_not_found"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"

    # Processing errors
    PROCESSING_FAILED = "processing_failed"

    # Vector database errors
    VECTOR_DB_ERROR = "vector_db_error"
    VECTOR_DB_SEARCH_ERROR = "vector_db_search_error"

    # Database errors
    DATABASE_ERROR = "database_error"
