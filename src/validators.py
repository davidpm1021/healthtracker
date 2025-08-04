"""
Data validation schemas for Health Tracker API.
Uses Pydantic for request/response validation.
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import logging

# Set up logging for data format debugging
logger = logging.getLogger(__name__)


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


class FlexibleHealthDataPoint(BaseModel):
    """
    Flexible schema for Health Connect data that accepts multiple field name variations.
    Transforms incoming data to the internal HealthDataPoint format.
    """
    # Accept multiple possible field names for metric type
    metric: Optional[Union[str, MetricType]] = Field(None, alias="metric")
    type: Optional[Union[str, MetricType]] = Field(None, alias="type")
    
    # Accept multiple possible field names for timestamps
    start_time: Optional[str] = Field(None, alias="start_time")
    timestamp: Optional[str] = Field(None, alias="timestamp") 
    time: Optional[str] = Field(None, alias="time")
    end_time: Optional[str] = Field(None, alias="end_time")
    
    # Accept multiple possible field names for values
    value: Optional[float] = Field(None, alias="value")
    count: Optional[float] = Field(None, alias="count")
    steps: Optional[float] = Field(None, alias="steps")
    
    # Optional unit with smart defaults
    unit: Optional[str] = Field(None, alias="unit")
    
    # Other fields
    source: Optional[DataSource] = Field(default=DataSource.HEALTH_CONNECT, alias="source")
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    
    # Store original data for debugging
    _original_data: Optional[Dict[str, Any]] = None
    
    class Config:
        """Allow field aliases and extra fields."""
        allow_population_by_field_name = True
        extra = "allow"  # Allow extra fields for flexibility
        fields = {'_original_data': {'exclude': True}}  # Exclude internal field from validation
    
    @root_validator(pre=True)
    def capture_original_data(cls, values):
        """Capture original data for debugging before transformation."""
        if isinstance(values, dict):
            # Store a copy of original data for logging
            values['_original_data'] = values.copy()
        return values
    
    @root_validator
    def transform_to_internal_format(cls, values):
        """Transform flexible input to internal HealthDataPoint format."""
        original_data = values.get('_original_data', {})
        
        # 1. Determine metric type from multiple possible fields
        metric_value = None
        for field in ['metric', 'type']:
            if field in values and values[field] is not None:
                metric_value = values[field]
                break
        
        if not metric_value:
            raise ValueError("Missing metric type. Expected 'metric' or 'type' field.")
        
        # Map common Health Connect types to internal types
        metric_mapping = {
            # Samsung Health / Health Connect types
            'com.samsung.health.step_count': MetricType.STEPS,
            'Steps': MetricType.STEPS,
            'STEPS': MetricType.STEPS,
            'step_count': MetricType.STEPS,
            'steps': MetricType.STEPS,
            
            'com.samsung.health.sleep': MetricType.SLEEP,
            'Sleep': MetricType.SLEEP,
            'SLEEP': MetricType.SLEEP,
            'sleep': MetricType.SLEEP,
            
            'com.samsung.health.weight': MetricType.WEIGHT,
            'Weight': MetricType.WEIGHT,
            'WEIGHT': MetricType.WEIGHT,
            'weight': MetricType.WEIGHT,
            'body_weight': MetricType.WEIGHT,
            
            'com.samsung.health.heart_rate': MetricType.HEART_RATE,
            'HeartRate': MetricType.HEART_RATE,
            'HEART_RATE': MetricType.HEART_RATE,
            'heart_rate': MetricType.HEART_RATE,
            'pulse': MetricType.HEART_RATE,
        }
        
        # Convert string to MetricType if needed
        if isinstance(metric_value, str):
            normalized_metric = metric_mapping.get(metric_value, metric_value.lower())
            if normalized_metric in [m.value for m in MetricType]:
                values['metric'] = MetricType(normalized_metric)
            elif isinstance(normalized_metric, MetricType):
                values['metric'] = normalized_metric
            else:
                raise ValueError(f"Unsupported metric type: {metric_value}. Supported types: {list(metric_mapping.keys())}")
        else:
            values['metric'] = metric_value
        
        # 2. Determine timestamp from multiple possible fields
        timestamp_value = None
        for field in ['start_time', 'timestamp', 'time']:
            if field in values and values[field] is not None:
                timestamp_value = values[field]
                break
        
        if not timestamp_value:
            raise ValueError("Missing timestamp. Expected 'start_time', 'timestamp', or 'time' field.")
        
        values['start_time'] = timestamp_value
        
        # 3. Determine value from multiple possible fields
        numeric_value = None
        for field in ['value', 'count', 'steps']:
            if field in values and values[field] is not None:
                numeric_value = values[field]
                break
        
        if numeric_value is None:
            raise ValueError("Missing numeric value. Expected 'value', 'count', or 'steps' field.")
        
        values['value'] = float(numeric_value)
        
        # 4. Set smart defaults for unit based on metric type if not provided
        if not values.get('unit'):
            unit_defaults = {
                MetricType.STEPS: 'count',
                MetricType.SLEEP: 'minutes', 
                MetricType.WEIGHT: 'kg',
                MetricType.HEART_RATE: 'bpm'
            }
            values['unit'] = unit_defaults.get(values['metric'], 'unknown')
        
        # Clean up the temporary fields that aren't part of final model
        for temp_field in ['type', 'timestamp', 'time', 'count', 'steps', '_original_data']:
            if temp_field in values:
                del values[temp_field]
        
        # Log the transformation for debugging
        logger.info(f"Transformed Health Connect data: {original_data} -> metric={values['metric']}, value={values['value']}, unit={values['unit']}")
        
        return values
    
    def to_health_data_point(self) -> HealthDataPoint:
        """Convert to internal HealthDataPoint format."""
        return HealthDataPoint(
            metric=self.metric,
            start_time=self.start_time,
            end_time=self.end_time,
            value=self.value,
            unit=self.unit,
            source=self.source,
            metadata=self.metadata
        )


class FlexibleHealthDataBatch(BaseModel):
    """
    Flexible schema for batch health data ingestion that accepts multiple formats.
    Automatically transforms to internal format.
    """
    data_points: List[Union[Dict[str, Any], HealthDataPoint, FlexibleHealthDataPoint]] = Field(..., description="List of health data points in various formats")
    sync_info: Optional[Dict[str, Any]] = Field(default=None, description="Synchronization metadata")
    
    @validator('data_points', pre=True)
    def transform_data_points(cls, v):
        """Transform data points to internal format."""
        if not v:
            raise ValueError('data_points cannot be empty')
        
        if len(v) > 1000:
            raise ValueError('Too many data points in single request (max 1000)')
        
        transformed_points = []
        
        for i, point in enumerate(v):
            try:
                if isinstance(point, dict):
                    # Try to parse as flexible format first
                    try:
                        flexible_point = FlexibleHealthDataPoint(**point)
                        health_point = flexible_point.to_health_data_point()
                        transformed_points.append(health_point)
                    except Exception as e:
                        # If flexible parsing fails, try direct HealthDataPoint parsing
                        try:
                            health_point = HealthDataPoint(**point)
                            transformed_points.append(health_point)
                        except Exception as e2:
                            raise ValueError(f"Data point {i} parsing failed. Tried flexible format: {str(e)}, tried direct format: {str(e2)}")
                elif isinstance(point, FlexibleHealthDataPoint):
                    health_point = point.to_health_data_point()
                    transformed_points.append(health_point)
                elif isinstance(point, HealthDataPoint):
                    transformed_points.append(point)
                else:
                    raise ValueError(f"Data point {i} has invalid type: {type(point)}")
                    
            except Exception as e:
                raise ValueError(f"Error processing data point {i}: {str(e)}")
        
        return transformed_points
    
    def to_health_data_batch(self) -> 'HealthDataBatch':
        """Convert to the original HealthDataBatch format."""
        return HealthDataBatch(
            data_points=self.data_points,
            sync_info=self.sync_info
        )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "data_points": [
                    {
                        "type": "Steps", 
                        "count": 1234,
                        "timestamp": "2024-01-20T10:00:00Z"
                    },
                    {
                        "type": "com.samsung.health.step_count",
                        "value": 1234,
                        "time": "2024-01-20T10:00:00Z"
                    },
                    {
                        "metric": "steps",
                        "start_time": "2024-01-01T10:00:00Z",
                        "value": 1500.0,
                        "unit": "steps",
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


class HealthDataBatch(BaseModel):
    """Schema for batch health data ingestion (internal format)."""
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