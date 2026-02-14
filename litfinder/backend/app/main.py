"""
LitFinder - AI-powered Academic Literature Platform
Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import search, bibliography, auth, user, collections, research
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="LitFinder API",
    description="ИИ-платформа подбора академической литературы",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(bibliography.router, prefix="/api/v1", tags=["Bibliography"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(research.router, prefix="/api/v1/research", tags=["Research Assistant"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "litfinder-api"
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "LitFinder API",
        "version": "0.1.0",
        "docs": "/docs"
    }
