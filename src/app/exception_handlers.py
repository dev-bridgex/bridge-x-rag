from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from app.models import ResponseSignal

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler that formats HTTPExceptions to include response signals.
    """
    # Default to invalid request
    signal = ResponseSignal.INVALID_REQUEST.value
    
    # Map status codes to signals
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        signal = ResponseSignal.INVALID_REQUEST.value
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        # Check if it's a project or file not found based on the detail message
        if "project" in exc.detail.lower():
            signal = ResponseSignal.PROJECT_NOT_FOUND.value
        elif "file" in exc.detail.lower():
            signal = ResponseSignal.FILE_NOT_FOUND.value
        else:
            signal = ResponseSignal.FILE_NOT_FOUND.value
    elif exc.status_code == status.HTTP_409_CONFLICT:
        signal = ResponseSignal.RESOURCE_CONFLICT.value
    elif exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        signal = ResponseSignal.FILE_SIZE_EXCEEDED.value
    elif exc.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        signal = ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
    elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        signal = ResponseSignal.VALIDATION_ERROR.value
    elif exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        signal = ResponseSignal.DATABASE_ERROR.value
    elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        signal = ResponseSignal.SERVICE_UNAVAILABLE.value
    
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
            "signal": ResponseSignal.VALIDATION_ERROR.value,
            "detail": "Validation error",
            "errors": error_messages
        }
    ) 