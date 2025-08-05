"""
Manual data entry API endpoints for Health Tracker.
Handles user-input data like HRV, mood, energy levels, and notes.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

from ..database import DatabaseManager
from ..models import ManualEntry, ManualMetricType
# from ..auth import require_auth  # Disabled for local development

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class ManualEntryRequest(BaseModel):
    """Request model for manual data entry."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    metric: str = Field(..., description="Metric type (hrv, mood, energy, notes)")
    value: Optional[float] = Field(None, description="Numeric value (optional)")
    unit: Optional[str] = Field(None, description="Unit for numeric values")
    text_value: Optional[str] = Field(None, description="Text value for non-numeric entries")
    notes: Optional[str] = Field(None, description="Additional notes or context")

    @validator('date')
    def validate_date(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @validator('metric')
    def validate_metric(cls, v):
        """Validate metric type."""
        if v not in ManualMetricType.all():
            raise ValueError(f'Invalid metric type. Must be one of: {ManualMetricType.all()}')
        return v

    @validator('value')
    def validate_value_constraints(cls, v, values):
        """Validate value constraints based on metric type."""
        if v is not None:
            metric = values.get('metric')
            if metric == ManualMetricType.HRV:
                if v < 0 or v > 1000:
                    raise ValueError('HRV value must be between 0 and 1000 ms')
            elif metric == ManualMetricType.MOOD:
                if v < 1 or v > 10:
                    raise ValueError('Mood score must be between 1 and 10')
            elif metric == ManualMetricType.ENERGY:
                if v < 1 or v > 10:
                    raise ValueError('Energy score must be between 1 and 10')
        return v

    @validator('unit')
    def validate_unit_requirements(cls, v, values):
        """Validate unit requirements based on metric and value."""
        metric = values.get('metric')
        value = values.get('value')
        
        if value is not None and metric == ManualMetricType.HRV:
            if v not in ['ms', 'milliseconds']:
                raise ValueError('HRV unit must be ms or milliseconds')
        elif value is not None and metric in [ManualMetricType.MOOD, ManualMetricType.ENERGY]:
            if v not in ['score', 'rating']:
                raise ValueError('Mood/Energy unit must be score or rating')
        
        return v

    class Config:
        schema_extra = {
            "example": {
                "date": "2024-08-03",
                "metric": "hrv",
                "value": 42.5,
                "unit": "ms",
                "notes": "Morning HRV reading after good sleep"
            }
        }


class ManualEntryBatch(BaseModel):
    """Request model for batch manual data entry."""
    entries: List[ManualEntryRequest] = Field(..., description="List of manual entries")

    @validator('entries')
    def validate_entries_not_empty(cls, v):
        """Ensure at least one entry is provided."""
        if not v:
            raise ValueError('At least one entry must be provided')
        if len(v) > 100:
            raise ValueError('Maximum 100 entries per batch')
        return v


class ManualEntryResponse(BaseModel):
    """Response model for manual data entry."""
    id: int
    date: str
    metric: str
    value: Optional[float]
    unit: Optional[str]
    text_value: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str


class ManualEntryBatchResponse(BaseModel):
    """Response model for batch manual data entry."""
    entries_processed: int
    entries_created: int
    entries_updated: int
    entries: List[ManualEntryResponse]


@router.post("/manual", response_model=ManualEntryResponse)
async def create_manual_entry(
    request: Request,
    entry_request: ManualEntryRequest):
    """
    Create or update a manual data entry.
    
    This endpoint allows users to input manual health data like HRV readings,
    mood scores, energy levels, and notes.
    """
    try:
        # Create manual entry object
        manual_entry = ManualEntry(
            date=entry_request.date,
            metric=entry_request.metric,
            value=entry_request.value,
            unit=entry_request.unit,
            text_value=entry_request.text_value,
            notes=entry_request.notes
        )
        
        # Store in database
        db = DatabaseManager()
        entry_id = db.insert_manual_entry(manual_entry)
        
        if not entry_id:
            raise HTTPException(status_code=500, detail="Failed to create manual entry")
        
        # Retrieve the created entry to return full data
        created_entry = db.get_manual_entry(entry_request.date, entry_request.metric)
        
        if not created_entry:
            raise HTTPException(status_code=500, detail="Failed to retrieve created entry")
        
        logger.info(f"Manual entry created: {entry_request.metric} for {entry_request.date}")
        
        return ManualEntryResponse(
            id=created_entry['id'],
            date=created_entry['date'],
            metric=created_entry['metric'],
            value=created_entry['value'],
            unit=created_entry['unit'],
            text_value=created_entry['text_value'],
            notes=created_entry['notes'],
            created_at=created_entry['created_at'],
            updated_at=created_entry['updated_at']
        )
        
    except ValueError as e:
        logger.warning(f"Invalid manual entry data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating manual entry: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/manual/batch", response_model=ManualEntryBatchResponse)
async def create_manual_entries_batch(
    request: Request,
    batch_request: ManualEntryBatch):
    """
    Create or update multiple manual data entries in a batch.
    
    This endpoint allows bulk import of manual health data.
    """
    try:
        db = DatabaseManager()
        
        entries_processed = 0
        entries_created = 0
        entries_updated = 0
        created_entries = []
        
        for entry_request in batch_request.entries:
            try:
                # Check if entry already exists
                existing_entry = db.get_manual_entry(entry_request.date, entry_request.metric)
                is_update = existing_entry is not None
                
                # Create manual entry object
                manual_entry = ManualEntry(
                    date=entry_request.date,
                    metric=entry_request.metric,
                    value=entry_request.value,
                    unit=entry_request.unit,
                    text_value=entry_request.text_value,
                    notes=entry_request.notes
                )
                
                # Store in database
                entry_id = db.insert_manual_entry(manual_entry)
                
                if entry_id:
                    entries_processed += 1
                    if is_update:
                        entries_updated += 1
                    else:
                        entries_created += 1
                    
                    # Retrieve the created/updated entry
                    created_entry = db.get_manual_entry(entry_request.date, entry_request.metric)
                    if created_entry:
                        created_entries.append(ManualEntryResponse(
                            id=created_entry['id'],
                            date=created_entry['date'],
                            metric=created_entry['metric'],
                            value=created_entry['value'],
                            unit=created_entry['unit'],
                            text_value=created_entry['text_value'],
                            notes=created_entry['notes'],
                            created_at=created_entry['created_at'],
                            updated_at=created_entry['updated_at']
                        ))
                else:
                    logger.warning(f"Failed to process entry: {entry_request.metric} for {entry_request.date}")
                    
            except ValueError as e:
                logger.warning(f"Invalid entry in batch: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing batch entry: {e}")
                continue
        
        logger.info(f"Batch manual entry: {entries_processed} processed, {entries_created} created, {entries_updated} updated")
        
        return ManualEntryBatchResponse(
            entries_processed=entries_processed,
            entries_created=entries_created,
            entries_updated=entries_updated,
            entries=created_entries
        )
        
    except Exception as e:
        logger.error(f"Error processing manual entry batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/manual/{metric}")
async def get_manual_entries(
    metric: str,
    start_date: str,
    end_date: str):
    """
    Get manual entries for a specific metric within a date range.
    """
    try:
        # Validate metric
        if metric not in ManualMetricType.all():
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid metric type. Must be one of: {ManualMetricType.all()}"
            )
        
        # Validate dates
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
        
        # Get entries from database
        db = DatabaseManager()
        entries = db.get_manual_entries(metric, start_date, end_date)
        
        # Convert to response format
        response_entries = [
            ManualEntryResponse(
                id=entry['id'],
                date=entry['date'],
                metric=entry['metric'],
                value=entry['value'],
                unit=entry['unit'],
                text_value=entry['text_value'],
                notes=entry['notes'],
                created_at=entry['created_at'],
                updated_at=entry['updated_at']
            )
            for entry in entries
        ]
        
        return {
            "metric": metric,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(response_entries),
            "entries": response_entries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving manual entries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/manual/{metric}/{date}")
async def delete_manual_entry(
    metric: str,
    date: str):
    """
    Delete a specific manual entry.
    """
    try:
        # Validate metric
        if metric not in ManualMetricType.all():
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid metric type. Must be one of: {ManualMetricType.all()}"
            )
        
        # Validate date
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
        
        # Delete from database
        db = DatabaseManager()
        success = db.delete_manual_entry(date, metric)
        
        if not success:
            raise HTTPException(status_code=404, detail="Manual entry not found")
        
        logger.info(f"Manual entry deleted: {metric} for {date}")
        
        return {"message": "Manual entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting manual entry: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")