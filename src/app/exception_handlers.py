from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from app.models.enums.ErrorTypes import ErrorType
from app.routes.schemas.base import ErrorResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler that formats HTTPExceptions to include error type.

    This handler automatically maps HTTP status codes to appropriate error types.
    It also supports custom error types through the exc.detail dictionary if provided.

    Args:
        request: FastAPI request object (required by FastAPI but not used)
        exc: The HTTP exception to handle
    """
    # Check if detail is a dictionary with a type key
    if isinstance(exc.detail, dict) and "type" in exc.detail:
        # Extract type and detail from the dictionary
        error_type = exc.detail["type"]
        detail = exc.detail.get("detail", "An error occurred")
    else:
        # Default to mapping based on status code and detail string
        detail = str(exc.detail)

        # Default to invalid request
        error_type = ErrorType.INVALID_REQUEST.value

        # Map status codes to error types
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            error_type = ErrorType.INVALID_REQUEST.value
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            # Check what type of resource is not found based on the detail message
            detail_lower = detail.lower()
            if "knowledge base" in detail_lower:
                error_type = ErrorType.KNOWLEDGE_BASE_NOT_FOUND.value
            elif "asset" in detail_lower:
                error_type = ErrorType.ASSET_NOT_FOUND.value
            elif "file" in detail_lower:
                error_type = ErrorType.FILE_NOT_FOUND.value
            else:
                # Default for 404 errors
                error_type = ErrorType.INVALID_REQUEST.value
        elif exc.status_code == status.HTTP_409_CONFLICT:
            error_type = ErrorType.RESOURCE_CONFLICT.value
        elif exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
            error_type = ErrorType.FILE_SIZE_EXCEEDED.value
        elif exc.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            error_type = ErrorType.FILE_TYPE_NOT_SUPPORTED.value
        elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            error_type = ErrorType.VALIDATION_ERROR.value
        elif exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            # Check for processing errors
            detail_lower = detail.lower()
            if "process" in detail_lower:
                error_type = ErrorType.PROCESSING_FAILED.value
            elif "index" in detail_lower or "vector" in detail_lower:
                error_type = ErrorType.VECTOR_DB_ERROR.value
            elif "search" in detail_lower:
                error_type = ErrorType.VECTOR_DB_SEARCH_ERROR.value
            else:
                error_type = ErrorType.DATABASE_ERROR.value
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            error_type = ErrorType.SERVICE_UNAVAILABLE.value

    # Use the ErrorResponse schema for consistent error formatting
    error_response = ErrorResponse(
        type=error_type,
        detail=detail,
        errors=None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return them in a consistent format

    Args:
        request: FastAPI request object (required by FastAPI but not used)
        exc: The validation exception to handle
    """
    errors = exc.errors()
    error_messages = []

    for error in errors:
        error_messages.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })

    # Use the ErrorResponse schema for consistent error formatting
    error_response = ErrorResponse(
        type=ErrorType.VALIDATION_ERROR.value,
        detail="Validation error",
        errors=error_messages
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


def raise_http_exception(status_code: int, error_type: str, detail: str) -> None:
    """
    Helper function to raise an HTTPException with a specific error type.

    This function simplifies raising exceptions with specific error types that will be
    properly handled by the http_exception_handler.

    Args:
        status_code: HTTP status code
        error_type: Error type from ErrorType enum
        detail: Error message

    Raises:
        HTTPException: With the specified status code and detail containing the error type
    """
    raise HTTPException(
        status_code=status_code,
        detail={"type": error_type, "detail": detail}
    )


# Convenience functions for common exceptions
def raise_knowledge_base_not_found(knowledge_base_id: str) -> None:
    """
    Raise a 404 exception for knowledge base not found with the appropriate error type.

    Args:
        knowledge_base_id: ID of the knowledge base that was not found
    """
    raise_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        error_type=ErrorType.KNOWLEDGE_BASE_NOT_FOUND.value,
        detail=f"Knowledge base with ID '{knowledge_base_id}' not found"
    )


def raise_asset_not_found(asset_id: str) -> None:
    """
    Raise a 404 exception for asset not found with the appropriate error type.

    Args:
        asset_id: ID of the asset that was not found
    """
    raise_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        error_type=ErrorType.ASSET_NOT_FOUND.value,
        detail=f"Asset with ID '{asset_id}' not found"
    )


def raise_file_not_found(file_id: str) -> None:
    """
    Raise a 404 exception for file not found with the appropriate error type.

    Args:
        file_id: ID of the file that was not found
    """
    raise_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        error_type=ErrorType.FILE_NOT_FOUND.value,
        detail=f"File with ID '{file_id}' not found"
    )


def raise_file_type_not_supported(file_type: str) -> None:
    """
    Raise a 415 exception for unsupported file type with the appropriate error type.

    Args:
        file_type: The unsupported file type
    """
    raise_http_exception(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        error_type=ErrorType.FILE_TYPE_NOT_SUPPORTED.value,
        detail=f"File type '{file_type}' is not supported"
    )


def raise_file_size_exceeded(file_size: int, max_size: int) -> None:
    """
    Raise a 413 exception for file size exceeded with the appropriate error type.

    Args:
        file_size: The size of the file in bytes
        max_size: The maximum allowed size in bytes
    """
    raise_http_exception(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        error_type=ErrorType.FILE_SIZE_EXCEEDED.value,
        detail=f"File size ({file_size} bytes) exceeds the maximum allowed size ({max_size} bytes)"
    )


def raise_processing_failed(detail: str) -> None:
    """
    Raise a 500 exception for processing failure with the appropriate error type.

    Args:
        detail: Details about the processing failure
    """
    raise_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type=ErrorType.PROCESSING_FAILED.value,
        detail=detail
    )


def raise_vector_db_error(detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
    """
    Raise an exception for vector database error with the appropriate error type.

    Args:
        detail: Details about the vector database error
        status_code: HTTP status code (default: 500)
    """
    raise_http_exception(
        status_code=status_code,
        error_type=ErrorType.VECTOR_DB_ERROR.value,
        detail=detail
    )


def raise_search_error(detail: str) -> None:
    """
    Raise a 500 exception for search error with the appropriate error type.

    Args:
        detail: Details about the search error
    """
    raise_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
        detail=detail
    )


def raise_resource_conflict(resource_type: str, resource_name: str) -> None:
    """
    Raise a 409 exception for resource conflict with the appropriate error type.

    This is typically used when a resource with the same name already exists.

    Args:
        resource_type: Type of resource (e.g., 'knowledge base', 'asset')
        resource_name: Name of the resource that conflicts
    """
    raise_http_exception(
        status_code=status.HTTP_409_CONFLICT,
        error_type=ErrorType.RESOURCE_CONFLICT.value,
        detail=f"{resource_type.capitalize()} with name '{resource_name}' already exists"
    )