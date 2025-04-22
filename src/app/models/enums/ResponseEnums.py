from enum import Enum

class ResponseSignalEnum(Enum):
    
    FILE_VALIDATED_SUCCESS = "file_validated_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_failed" 
    FILE_ID_ERROR = "no_file_found_with_this_id"
    
    PROCESSING_SUCCESS = "processing_success"
    PROCESSING_FAILED = "processing_failed"
    
    NO_FILES_ERROR = "no_files_found"
    
    INVALID_REQUEST = "invalid_request"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RESOURCE_CONFLICT = "resource_conflict"
    
    INDEXING_PROJECT_INTO_VECTORDB_ERROR = "error_while_indexing_project_into_vector_db"
    INSERT_INTO_VECTORDB_ERROR = "insert_into_vectordb_error"
    INSERT_INTO_VECTORDB_SUCCESS = "insert_into_vectordb_success"
    VECTORDB_COLLECTION_RETRIEVED = "vectordb_collection_retrieved"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    VECTORDB_SEARCH_SUCCESS = "vectordb_search_success"
    RAG_ANSWER_ERROR = "rag_answer_error"
    RAG_ANSWER_SUCCESS = "rag_answer_success"
    
    
