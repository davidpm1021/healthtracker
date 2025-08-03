"""
Data validation schemas for Health Tracker API.
Uses Pydantic for request/response validation.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Supported health metric types for automated ingestion."""
    STEPS = "steps"
    SLEEP = "sleep"
    WEIGHT = "weight"
    HEART_RATE = "heart_rate"


class DataSource(str, Enum):
    """Supported data sources."""
    HEALTH_CONNECT = "health_connect"
    MANUAL = "manual"
    IMPORT = "import"
    TASKER = "tasker"


class HealthDataPoint(BaseModel):
    """Schema for a single health data point."""
    metric: MetricType = Field(..., description="Type of health metric")
    start_time: str = Field(..., description="Start time in ISO format")
    end_time: Optional[str] = Field(None, description="End time in ISO format (optional)")
    value: float = Field(..., description="Numeric value of the metric")
    unit: str = Field(..., description="Unit of measurement")
    source: DataSource = Field(default=DataSource.HEALTH_CONNECT, description="Data source")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @validator('start_time')
    def validate_start_time(cls, v):
        """Validate start_time is a valid ISO format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('start_time must be in ISO format')
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate end_time if provided."""
        if v is None:
            return v
        
        try:
            end_dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(values['start_time'].replace('Z', '+00:00'))
            
            if end_dt < start_dt:
                raise ValueError('end_time must be after start_time')
            
            return v
        except ValueError as e:
            if 'end_time must be after start_time' in str(e):
                raise e
            raise ValueError('end_time must be in ISO format')
    
    @validator('value')
    def validate_value(cls, v, values):
        """Validate value based on metric type."""
        if 'metric' not in values:
            return v
        
        metric = values['metric']
        
        # Value must be non-negative for all metrics
        if v < 0:
            raise ValueError(f'{metric} value must be non-negative')
        
        # Metric-specific validations
        if metric == MetricType.STEPS:
            if v > 100000:  # Reasonable upper limit for daily steps
                raise ValueError('Steps value seems unreasonably high (>100,000)')
        
        elif metric == MetricType.SLEEP:
            if v > 1440:  # More than 24 hours
                raise ValueError('Sleep value cannot exceed 1440 minutes (24 hours)')
        
        elif metric == MetricType.WEIGHT:
            if v > 1000 or v < 1:  # Reasonable weight range in kg
                raise ValueError('Weight must be between 1-1000 kg')
        
        elif metric == MetricType.HEART_RATE:
            if v > 250 or v < 30:  # Reasonable heart rate range in bpm
                raise ValueError('Heart rate must be between 30-250 bpm')
        
        return v
    
    @validator('unit')
    def validate_unit(cls, v, values):
        """Validate unit matches metric type."""
        if 'metric' not in values:
            return v
        
        metric = values['metric']
        valid_units = {
            MetricType.STEPS: ['steps', 'count'],
            MetricType.SLEEP: ['minutes', 'min', 'hours', 'h'],
            MetricType.WEIGHT: ['kg', 'kilograms', 'lbs', 'pounds'],
            MetricType.HEART_RATE: ['bpm', 'beats_per_minute']
        }
        
        if metric in valid_units and v.lower() not in [u.lower() for u in valid_units[metric]]:
            raise ValueError(f'Invalid unit "{v}" for metric "{metric}". Valid units: {valid_units[metric]}')
        
        return v


class HealthDataBatch(BaseModel):
    """Schema for batch health data ingestion."""
    data_points: List[HealthDataPoint] = Field(..., description="List of health data points")
    sync_info: Optional[Dict[str, Any]] = Field(default=None, description="Synchronization metadata")
    
    @validator('data_points')
    def validate_data_points(cls, v):
        """Validate data points list."""
        if not v:
            raise ValueError('data_points cannot be empty')
        
        if len(v) > 1000:  # Configurable limit
            raise ValueError('Too many data points in single request (max 1000)')
        
        return v
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "data_points": [
                    {
                        "metric": "steps",
                        "start_time": "2024-01-01T10:00:00Z",
                        "value": 1500.0,
                        "unit": "steps",
                        "source": "health_connect"
                    },
                    {
                        "metric": "heart_rate",
                        "start_time": "2024-01-01T08:00:00Z",
                        "value": 72.0,
                        "unit": "bpm",
                        "source": "health_connect"
                    }
                ],
                "sync_info": {
                    "sync_id": "sync-123456",
                    "device_id": "phone-abc",
                    "app_version": "1.0.0"
                }
            }
        }


class IngestionResponse(BaseModel):
    """Schema for ingestion API response."""
    success: bool = Field(..., description="Whether ingestion was successful")
    processed_count: int = Field(..., description="Number of data points processed")
    added_count: int = Field(..., description="Number of new data points added")
    updated_count: int = Field(..., description="Number of data points updated")
    skipped_count: int = Field(..., description="Number of data points skipped (duplicates)")
    errors: List[str] = Field(default=[], description="List of error messages")
    sync_id: Optional[str] = Field(None, description="Sync operation ID")
    timestamp: str = Field(..., description="Response timestamp")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "processed_count": 2,
                "added_count": 2,
                "updated_count": 0,
                "skipped_count": 0,
                "errors": [],
                "sync_id": "sync-123456",
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }


class ValidationError(BaseModel):
    """Schema for validation error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    value: Optional[Any] = Field(None, description="Invalid value")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Steps value seems unreasonably high (>100,000)",
                "field": "value",
                "value": 150000
            }
        }


def validate_health_data_batch(data: dict) -> HealthDataBatch:
    """
    Validate and parse health data batch.
    
    Args:
        data: Raw data dictionary
        
    Returns:
        Validated HealthDataBatch instance
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return HealthDataBatch(**data)
    except Exception as e:
        raise ValueError(f"Data validation failed: {str(e)}")


def normalize_units(data_point: HealthDataPoint) -> HealthDataPoint:
    """
    Normalize units to standard internal units.
    
    Args:
        data_point: Health data point to normalize
        
    Returns:
        Data point with normalized units
    """
    # Create a copy to avoid modifying original
    normalized = data_point.copy()
    
    # Normalize based on metric type
    if data_point.metric == MetricType.SLEEP:
        if data_point.unit.lower() in ['hours', 'h']:
            normalized.value = data_point.value * 60  # Convert to minutes
            normalized.unit = 'minutes'
    
    elif data_point.metric == MetricType.WEIGHT:
        if data_point.unit.lower() in ['lbs', 'pounds']:
            normalized.value = data_point.value * 0.453592  # Convert to kg
            normalized.unit = 'kg'
    
    elif data_point.metric == MetricType.HEART_RATE:
        if data_point.unit.lower() in ['beats_per_minute']:
            normalized.unit = 'bpm'  # Standardize to bpm
    
    return normalized