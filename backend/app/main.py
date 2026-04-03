"""
FastAPI application main entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.config import get_settings, ensure_directories
from app.database import init_db, close_db, get_db
from app.dependencies import create_default_admin
from app.middleware import setup_middleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    ensure_directories()
    await init_db()

    # Create default admin user
    async for db in get_db():
        await create_default_admin(db)
        break  # Only need one session

    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    yield

    # Shutdown
    await close_db()
    print("Application shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Document Intelligence System API - Extract structured data from documents using LLM",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Setup middleware
    setup_middleware(app)

    # Include API routers
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else None
        }

    return app


# Create application instance
app = create_application()
