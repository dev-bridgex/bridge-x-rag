import time
from fastapi import Request
from app.logging import get_logger

# Get a dedicated logger for the middleware
logger = get_logger(__name__)

async def logging_middleware(request: Request, call_next):
    """
    Middleware to log request details and timing information.
    
    Args:
        request: The incoming request
        call_next: The next middleware or route handler
        
    Returns:
        The response from the next handler
    """
    # Get client IP - handle proxy forwarding
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0] if forwarded_for else client_host
    
    # Log the request
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
    
    # Time the request processing
    start_time = time.time()
    
    # Process the request and catch any exceptions
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code
        
        # Log based on status code
        if status_code >= 500:
            logger.error(f"Response: {request.method} {request.url.path} - {status_code} - {process_time:.4f}s")
        elif status_code >= 400:
            logger.warning(f"Response: {request.method} {request.url.path} - {status_code} - {process_time:.4f}s")
        else:
            logger.info(f"Response: {request.method} {request.url.path} - {status_code} - {process_time:.4f}s")
            
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(f"Error during {request.method} {request.url.path} after {process_time:.4f}s: {str(e)}")
        raise 