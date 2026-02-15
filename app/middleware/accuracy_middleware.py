from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)


class AccuracyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):
        start_time = time.time()  # Start timing the request

        response = await call_next(request)  # Process the request

        duration = time.time() - start_time  # Calculate duration

        # Log the request path and response duration
        logger.info(f"Request: {request.url.path}, Duration: {duration:.4f} seconds")
        return response

# To use the middleware:
# app = FastAPI()
# app.add_middleware(AccuracyMiddleware)