"""
Health Tracker FastAPI Application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

# Import API routers
from .api.health import router as health_router
from .api.ingest import router as ingest_router
from .api.manual import router as manual_router
from .api.summaries import router as summaries_router
from .api.jobs import router as jobs_router
from .api.ui import router as ui_router
from .api.charts import router as charts_router
from .api.goals import router as goals_router
from .api.progress import router as progress_router
from .api.badges import router as badges_router

# Import scheduler and job registration
from .scheduler import initialize_scheduler
from .jobs import register_all_jobs

# Initialize FastAPI app
app = FastAPI(
    title="Health Tracker API",
    description="Local health data tracking and visualization API",
    version="1.0.0"
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(manual_router, prefix="/api")
app.include_router(summaries_router, prefix="/api")
app.include_router(jobs_router, prefix="/api/jobs")
app.include_router(ui_router, prefix="/api/ui")
app.include_router(charts_router, prefix="/api")
app.include_router(goals_router)
app.include_router(progress_router)
app.include_router(badges_router)

# Mount static files directory
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Root endpoint - serve the main dashboard
@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    return {"message": "Health Tracker API", "version": "1.0.0", "dashboard": "/static/index.html"}

# Health check endpoint at root level
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "health-tracker-api",
        "version": "1.0.0"
    }

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize background jobs on startup."""
    try:
        # Register all jobs with the scheduler
        scheduler = register_all_jobs()
        
        # Start the scheduler
        initialize_scheduler()
        
        print("✅ Background job scheduler initialized")
    except Exception as e:
        print(f"❌ Error initializing scheduler: {e}")


# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background jobs."""
    try:
        from scheduler import shutdown_scheduler
        shutdown_scheduler()
        print("✅ Background job scheduler shutdown complete")
    except Exception as e:
        print(f"❌ Error during scheduler shutdown: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)