"""
Health Tracker MVP - Single Clean Server
Local-only health data tracking with ingestion and visualization
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path

# Import only essential API routers for MVP
from .api.health import router as health_router
from .api.ingest import router as ingest_router
from .api.manual import router as manual_router
from .api.ui import router as ui_router
from .api.charts import router as charts_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healthtracker")

# Initialize FastAPI app
app = FastAPI(
    title="Health Tracker MVP",
    description="Simple local health data tracking and visualization",
    version="1.0.0"
)

# Add CORS middleware for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local-only, no auth needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include essential API routers
app.include_router(health_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")  # Critical for Tasker data
app.include_router(manual_router, prefix="/api")  # For HRV manual entry
app.include_router(ui_router, prefix="/api/ui")   # Dashboard views
app.include_router(charts_router, prefix="/api")  # Data visualization

# Mount static files for dashboard
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Static files mounted from {static_path}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Health Tracker MVP Running",
        "dashboard": "/static/index.html",
        "api_docs": "/docs",
        "health_check": "/api/health"
    }

# Simple health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "health-tracker-mvp"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)