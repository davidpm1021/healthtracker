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
    request: Request
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
    
    # Get and log the raw incoming data for debugging
    try:
        # Get raw request body for debugging
        body = await request.body()
        body_str = body.decode('utf-8')
        logger.info(f"Raw request body from {client_ip}: {body_str}")
        
        # Parse JSON from the body
        import json
        raw_data = json.loads(body_str)
        
    except Exception as e:
        logger.error(f"Failed to parse JSON from request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in request body: {str(e)}"
        )
    
    # Log the parsed data structure
    logger.info(f"Parsed request data: {raw_data}")
    logger.info(f"Data type: {type(raw_data)}, Keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
    
    # Log ingestion attempt with data format info
    logger.info(f"Starting flexible data ingestion from {client_ip}, sync_id: {sync_id}")
    
    # Try to parse as flexible batch
    try:
        # Validate the raw data structure
        if not isinstance(raw_data, dict):
            raise ValueError(f"Expected dict, got {type(raw_data)}")
        
        if 'data_points' not in raw_data:
            raise ValueError("Missing 'data_points' field in request")
        
        if not isinstance(raw_data['data_points'], list):
            raise ValueError("'data_points' must be a list")
        
        if not raw_data['data_points']:
            raise ValueError("'data_points' cannot be empty")
        
        # Log first data point for debugging
        logger.info(f"First data point structure: {raw_data['data_points'][0]}")
        
        # Detect and log the data format
        first_point = raw_data['data_points'][0]
        format_info = []
        
        # Check what fields are present
        if 'metric' in first_point: format_info.append("has 'metric'")
        if 'type' in first_point: format_info.append("has 'type'")
        if 'start_time' in first_point: format_info.append("has 'start_time'")
        if 'timestamp' in first_point: format_info.append("has 'timestamp'")
        if 'time' in first_point: format_info.append("has 'time'")
        if 'value' in first_point: format_info.append("has 'value'")
        if 'count' in first_point: format_info.append("has 'count'")
        if 'steps' in first_point: format_info.append("has 'steps'")
        if 'unit' in first_point: format_info.append("has 'unit'")
        
        logger.info(f"Data point format analysis: {', '.join(format_info)}")
        
        # Parse as flexible batch
        flexible_batch = FlexibleHealthDataBatch(**raw_data)
        internal_batch = flexible_batch.to_health_data_batch()
        logger.info(f"Successfully transformed {len(internal_batch.data_points)} data points to internal format")
        
        # Use the transformed data for processing
        data = internal_batch
        
    except Exception as e:
        logger.error(f"Failed to parse flexible data format: {str(e)}")
        logger.error(f"Raw data that failed: {raw_data}")
        
        # Try to provide helpful error message based on the data
        if isinstance(raw_data, dict) and 'data_points' in raw_data and raw_data['data_points']:
            first_point = raw_data['data_points'][0]
            missing_fields = []
            
            if not any(field in first_point for field in ['metric', 'type']):
                missing_fields.append("metric identifier (need 'metric' or 'type')")
            if not any(field in first_point for field in ['start_time', 'timestamp', 'time']):
                missing_fields.append("timestamp (need 'start_time', 'timestamp', or 'time')")
            if not any(field in first_point for field in ['value', 'count', 'steps']):
                missing_fields.append("numeric value (need 'value', 'count', or 'steps')")
            
            if missing_fields:
                detail_msg = f"Missing required fields: {', '.join(missing_fields)}. Received fields: {list(first_point.keys())}"
            else:
                detail_msg = f"Data format parsing failed: {str(e)}"
        else:
            detail_msg = f"Data format parsing failed: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg
        )
    
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