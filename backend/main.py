"""Agatha - AI-first ad spend optimization system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.logging_config import setup_logging
from routes.agent_routes import router as agent_router
from routes.auth_routes import router as auth_router
from routes.meta_routes import router as meta_router

# Set up structured logging
setup_logging(level="INFO", json_output=not settings.debug)

app = FastAPI(
    title="Agatha",
    description="AI-first ad spend optimization system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(meta_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agatha",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "ai_provider": settings.ai_provider,
        "model": settings.gemini_model if settings.ai_provider == "gemini" else settings.openai_model,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
