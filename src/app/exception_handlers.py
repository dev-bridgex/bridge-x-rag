from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from app.models import ResponseSignalEnum

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler that formats HTTPExceptions to include response signals.
    """
    # Default to invalid request
    signal = ResponseSignalEnum.INVALID_REQUEST.value
    
    # Map status codes to signals
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        signal = ResponseSignalEnum.INVALID_REQUEST.value
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        # Check if it's a project or file not found based on the detail message
        if "project" in exc.detail.lower():
            signal = ResponseSignalEnum.PROJECT_NOT_FOUND.value
        elif "file" in exc.detail.lower():
            signal = ResponseSignalEnum.FILE_NOT_FOUND.value
        else:
            signal = ResponseSignalEnum.FILE_NOT_FOUND.value
    elif exc.status_code == status.HTTP_409_CONFLICT:
        signal = ResponseSignalEnum.RESOURCE_CONFLICT.value
    elif exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        signal = ResponseSignalEnum.FILE_SIZE_EXCEEDED.value
    elif exc.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        signal = ResponseSignalEnum.FILE_TYPE_NOT_SUPPORTED.value
    elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        signal = ResponseSignalEnum.VALIDATION_ERROR.value
    elif exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        signal = ResponseSignalEnum.DATABASE_ERROR.value
    elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        signal = ResponseSignalEnum.SERVICE_UNAVAILABLE.value
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"signal": signal, "detail": exc.detail}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return them in a consistent format
    """
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        error_messages.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "signal": ResponseSignalEnum.VALIDATION_ERROR.value,
            "detail": "Validation error",
            "errors": error_messages
        }
    ) 