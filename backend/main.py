"""
Agatha Backend - FastAPI Application.

Multi-agent ad spend anomaly detection and optimization.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json

from config.settings import settings
from routes import auth_router, agent_router
from schemas.responses import HealthResponse

app = FastAPI(
    title="Agatha Ad Spend Optimization",
    description="Multi-agent system for ad spend anomaly detection and optimization",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(agent_router)


@app.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.environment,
    )


@app.get("/health")
async def health():
    """Alternative health check for Cloud Run."""
    return {"status": "healthy"}


@app.get("/api/track")
async def track_event(event: str, request: Request):
    """Simple event tracking - logs to Cloud Logging."""
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    referer = request.headers.get("referer", "direct")
    user_agent = request.headers.get("user-agent", "unknown")

    # Structured log for Cloud Logging
    log_entry = {
        "type": "TRACK",
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "ip": client_ip.split(",")[0].strip() if client_ip else "unknown",
        "referer": referer,
        "user_agent": user_agent,
    }
    print(f"TRACK: {json.dumps(log_entry)}")

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
