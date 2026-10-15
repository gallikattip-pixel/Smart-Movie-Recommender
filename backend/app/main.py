"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import HealthResponse
from app.api import search, recommend, feedback, favorites
from app.tmdb import init_tmdb_client, close_tmdb_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    await init_tmdb_client()
    yield
    # Shutdown
    await close_tmdb_client()


app = FastAPI(
    title="Smart Movie Recommender API",
    description="Personalized movie and TV series recommendations",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - only allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        tmdb_configured=settings.has_tmdb_credentials,
    )


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "Smart Movie Recommender API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }