"""
Health check endpoints for the Health Tracker API.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import psutil
import os

from ..database import DatabaseManager

router = APIRouter()

@router.get("/health")
async def api_health():
    """Detailed API health check with system information."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "health-tracker-api",
            "version": "1.0.0",
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "python_version": sys.version.split()[0]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health/db")
async def database_health():
    """Database connectivity and status check."""
    try:
        db = DatabaseManager()
        
        # Test database connection
        if not db.test_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Get table counts
        counts = db.get_table_counts()
        
        # Get database file info
        db_path = db.db_path
        db_size = 0
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "connected": True,
                "path": db_path,
                "size_bytes": db_size,
                "tables": counts
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")

@router.get("/health/storage")
async def storage_health():
    """Storage and file system health check."""
    try:
        # Check main directories
        project_root = Path(__file__).parent.parent.parent
        static_dir = project_root / "static"
        database_dir = project_root / "database"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "storage": {
                "project_root": str(project_root),
                "directories": {
                    "static": {
                        "exists": static_dir.exists(),
                        "path": str(static_dir)
                    },
                    "database": {
                        "exists": database_dir.exists(),
                        "path": str(database_dir)
                    }
                },
                "disk_usage": {
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                    "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
                    "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                    "percent_used": psutil.disk_usage('/').percent
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage health check failed: {str(e)}")

@router.get("/health/all")
async def comprehensive_health():
    """Comprehensive health check combining all checks."""
    try:
        # Get all health check results
        api_health_result = await api_health()
        db_health_result = await database_health()
        storage_health_result = await storage_health()
        
        # Determine overall status
        all_healthy = all([
            api_health_result["status"] == "healthy",
            db_health_result["status"] == "healthy",
            storage_health_result["status"] == "healthy"
        ])
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "api": api_health_result,
                "database": db_health_result,
                "storage": storage_health_result
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }