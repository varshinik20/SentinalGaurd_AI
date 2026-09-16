"""
SentinelGuard AI — Enterprise AI Security Gateway
Application entrypoint.

This file wires together the API router, middleware, and startup/shutdown
lifecycle hooks. Business logic lives in app/services/*, not here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# NOTE: api_router will be introduced in Module 1 (Authentication Service)
# and expanded in every subsequent module. Left as a placeholder import
# guard so this file doesn't break before that module exists.
try:
    from app.api.v1.router import api_router
except ImportError:
    api_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: place DB connection warm-up, FAISS index load, etc. here
    # as each module is implemented.
    yield
    # Shutdown: place cleanup (closing DB pools, flushing caches) here.


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI Security Gateway for Semantic Data Leakage Prevention",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if api_router is not None:
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness/readiness probe for load balancers and orchestrators."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
