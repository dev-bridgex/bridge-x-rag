import time
import logging
from fastapi import Request

async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(f"{request.method} {request.url.path} completed in {process_time:.4f}s with status {response.status_code}")
    return response 