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
    usage,
    playwright_bridge as playwright_bridge_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed default providers and recover interrupted runs from previous server restarts
    db = SessionLocal()
    try:
        provider_manager.seed_default_providers(db)
        from app.models.all_models import DiscussionRun, ModelResponse
        stale_runs = db.query(DiscussionRun).filter_by(status="in_progress").all()
        for sr in stale_runs:
            sr.status = "stopped"
        stale_resps = db.query(ModelResponse).filter_by(status="in_progress").all()
        for resp in stale_resps:
            resp.status = "pending"
        if stale_runs or stale_resps:
            db.commit()
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
app.include_router(playwright_bridge_router.router)


@app.get("/")
def root():
    return {
        "message": "Selamat datang di AI Council API",
        "status": "online",
        "docs_url": "/docs"
    }
