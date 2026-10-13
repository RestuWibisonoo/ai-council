from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.provider_manager import provider_manager
from app.routers import (
    health,
    discussions,
    research,
    documents,
    providers,
    usage
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed default providers
    db = SessionLocal()
    try:
        provider_manager.seed_default_providers(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Council — Multi-AI Discussion & Research Workspace Backend API",
    lifespan=lifespan
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(discussions.router)
app.include_router(discussions.conv_router)
app.include_router(research.router)
app.include_router(documents.router)
app.include_router(providers.router)
app.include_router(usage.router)


@app.get("/")
def root():
    return {
        "message": "Selamat datang di AI Council API",
        "status": "online",
        "docs_url": "/docs"
    }
