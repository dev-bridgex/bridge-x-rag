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
    
    PROJECT_NOT_FOUND = "project_not_found"
    NO_FILES_ERROR = "no_files_found"
    
    INVALID_REQUEST = "invalid_request"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RESOURCE_CONFLICT = "resource_conflict"

