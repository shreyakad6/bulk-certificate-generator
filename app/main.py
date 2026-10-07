import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routes.jobs import router as jobs_router
from app.routes.certificates import router as certificates_router

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bulk_certificate_generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info("Initializing database schema...")
    init_db()

    # Ensure storage folder exists
    os.makedirs(settings.GENERATED_FILES_DIR, exist_ok=True)
    logger.info("Storage directory verified at: %s", settings.GENERATED_FILES_DIR)

    yield

    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-ready backend API for bulk certificate generation. "
        "Accepts recipient lists, validates data, generates professional PDF certificates "
        "asynchronously, and provides status tracking and download endpoints."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Mount API Routers
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(certificates_router, prefix=settings.API_V1_PREFIX)


@app.get(
    "/",
    tags=["Root"],
    summary="Root API Info",
    description="Returns basic information about the service and link to Swagger documentation.",
)
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "health_check": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    description="Returns the operational health status of the service.",
)
def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }
