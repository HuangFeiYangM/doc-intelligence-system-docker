"""
FastAPI middleware configuration.
"""
import time
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.exceptions import AppException

settings = get_settings()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except AppException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "detail": e.detail,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            # Log the full traceback
            traceback_str = traceback.format_exc()
            print(f"Unhandled exception: {traceback_str}")

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(e) if settings.DEBUG else "An unexpected error occurred"
                }
            )


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Request timing and logging middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log request
        print(
            f"{request.method} {request.url.path} "
            f"- {response.status_code} - {process_time:.3f}s"
        )

        return response


def setup_middleware(app):
    """Configure all middleware for the application.

    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Request timing middleware
    app.add_middleware(RequestTimingMiddleware)
