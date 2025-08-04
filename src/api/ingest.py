"""
Data ingestion endpoints for Health Tracker API.
Handles ingestion of health data from mobile devices.
"""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import asyncio

# Add parent directories to path for imports
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validators import (
    HealthDataBatch, FlexibleHealthDataBatch, IngestionResponse, ValidationError,
    validate_health_data_batch, normalize_units
)
# from auth import require_auth, SecurityError  # Authentication removed for local-only setup
from database import DatabaseManager
from models import RawPoint, SyncLog, SyncStatus
from config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize database manager
db_manager = DatabaseManager()


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_health_data(
    request: Request,
    data: FlexibleHealthDataBatch
):
    """
    Ingest health data from mobile device.
    
    Accepts health data in multiple formats (Health Connect, Samsung Health, etc.)
    without authentication for local-only setup.
    
    Supported formats:
    - {"type": "Steps", "count": 1234, "timestamp": "2024-01-20T10:00:00Z"}
    - {"type": "com.samsung.health.step_count", "value": 1234, "time": "2024-01-20T10:00:00Z"}
    - {"metric": "steps", "start_time": "2024-01-01T10:00:00Z", "value": 1500.0, "unit": "steps"}
    
    Returns:
    - Processing statistics and any errors
    """
    config = get_config()
    
    # Get client IP for logging (without authentication checks)
    client_ip = request.client.host if request.client else "unknown"
    sync_id = f"sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{client_ip.replace('.', '')}"
    
    # Log ingestion attempt with data format info
    logger.info(f"Starting flexible data ingestion from {client_ip}, sync_id: {sync_id}")
    logger.info(f"Received {len(data.data_points)} data points in flexible format")
    
    # Convert flexible batch to internal format
    try:
        internal_batch = data.to_health_data_batch()
        logger.info(f"Successfully transformed {len(internal_batch.data_points)} data points to internal format")
    except Exception as e:
        logger.error(f"Failed to transform data to internal format: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data format transformation failed: {str(e)}"
        )
    
    # Use the transformed data for processing
    data = internal_batch
    
    # Initialize counters
    processed_count = 0
    added_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    
    # Start time for sync log
    start_time = datetime.now().isoformat()
    
    try:
        # Initialize database if needed
        db_manager.initialize_database()
        
        # Process each data point
        for i, data_point in enumerate(data.data_points):
            try:
                processed_count += 1
                
                # Normalize units to standard internal units
                normalized_point = normalize_units(data_point)
                
                # Create RawPoint model
                raw_point = RawPoint(
                    metric=normalized_point.metric.value,
                    start_time=normalized_point.start_time,
                    end_time=normalized_point.end_time,
                    value=normalized_point.value,
                    unit=normalized_point.unit,
                    source=normalized_point.source.value
                )
                
                # Insert into database
                row_id = db_manager.insert_raw_point(raw_point)
                
                if row_id is None:
                    # Duplicate entry
                    skipped_count += 1
                    logger.debug(f"Skipped duplicate data point {i}: {raw_point.metric} at {raw_point.start_time}")
                else:
                    added_count += 1
                    logger.debug(f"Added data point {i} with ID {row_id}: {raw_point.metric} = {raw_point.value}")
                
            except Exception as e:
                error_msg = f"Error processing data point {i}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Create sync log entry
        sync_log = SyncLog(
            source=data.data_points[0].source.value if data.data_points else "unknown",
            sync_type="incremental",
            start_time=start_time,
            end_time=datetime.now().isoformat(),
            records_processed=processed_count,
            records_added=added_count,
            records_updated=updated_count,
            status=SyncStatus.SUCCESS if not errors else SyncStatus.PARTIAL,
            error_message="; ".join(errors) if errors else None
        )
        
        db_manager.insert_sync_log(sync_log)
        
        # Create response
        response = IngestionResponse(
            success=len(errors) == 0,
            processed_count=processed_count,
            added_count=added_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            errors=errors,
            sync_id=sync_id,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Ingestion completed: {response.dict()}")
        
        return response
        
    except Exception as e:
        # Log the error
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg)
        
        # Create error sync log
        sync_log = SyncLog(
            source="unknown",
            sync_type="incremental",
            start_time=start_time,
            end_time=datetime.now().isoformat(),
            records_processed=processed_count,
            records_added=added_count,
            records_updated=updated_count,
            status=SyncStatus.ERROR,
            error_message=error_msg
        )
        
        try:
            db_manager.insert_sync_log(sync_log)
        except Exception:
            logger.error("Failed to log sync error to database")
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data ingestion failed: {str(e)}"
        )


@router.get("/ingest/status")
async def get_ingestion_status():
    """
    Get recent ingestion status and statistics.
    
    No authentication required for local-only setup.
    """
    try:
        db_manager.initialize_database()
        
        # Get recent sync logs
        recent_syncs = db_manager.get_recent_sync_logs(10)
        
        # Get table counts for statistics
        table_counts = db_manager.get_table_counts()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_raw_points": table_counts.get("raw_points", 0),
                "total_sync_logs": table_counts.get("sync_log", 0)
            },
            "recent_syncs": recent_syncs
        }
        
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion status: {str(e)}"
        )


@router.post("/ingest/test")
async def test_ingestion_endpoint(request: Request):
    """
    Test endpoint to verify ingestion API is working.
    
    Returns system information for local-only setup.
    """
    config = get_config()
    client_ip = request.client.host if request.client else "unknown"
    
    return {
        "status": "healthy",
        "message": "Ingestion endpoint is working",
        "timestamp": datetime.now().isoformat(),
        "client_info": {
            "ip": client_ip,
            "authenticated": False  # No authentication in local-only setup
        },
        "config_info": {
            "max_payload_size": config.max_payload_size,
            "max_records_per_request": config.max_records_per_request,
            "development_mode": config.is_development
        }
    }


# Note: Exception handlers should be registered on the main FastAPI app in main.py if needed