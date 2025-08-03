"""
Metrics processing module for Health Tracker.
Contains metric-specific normalization and processing logic.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)


class MetricProcessor:
    """Base class for metric-specific processors."""
    
    def __init__(self, metric_name: str):
        self.metric_name = metric_name
        self.logger = logging.getLogger(f"{__name__}.{metric_name}")
    
    def validate_points(self, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and filter metric-specific data points.
        Override in subclasses for metric-specific validation.
        """
        valid_points = []
        
        for point in points:
            if self._is_valid_point(point):
                valid_points.append(point)
            else:
                self.logger.warning(f"Invalid {self.metric_name} point: {point}")
        
        return valid_points
    
    def _is_valid_point(self, point: Dict[str, Any]) -> bool:
        """
        Basic validation for a data point.
        Override in subclasses for metric-specific validation.
        """
        required_fields = ['value', 'start_time', 'unit']
        
        for field in required_fields:
            if field not in point:
                return False
        
        try:
            value = float(point['value'])
            if value < 0:
                return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    def normalize(
        self, 
        date_str: str, 
        points: List[Dict[str, Any]], 
        existing_summary: Optional[Dict[str, Any]] = None
    ) -> Optional['DailySummary']:
        """
        Normalize raw points into a daily summary.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement normalize method")


def get_metric_units() -> Dict[str, List[str]]:
    """
    Get valid units for each metric type.
    
    Returns:
        Dictionary mapping metric names to lists of valid units
    """
    return {
        'steps': ['steps', 'count'],
        'sleep': ['minutes', 'min', 'hours', 'h'],
        'weight': ['kg', 'kilograms', 'lbs', 'pounds'],
        'heart_rate': ['bpm', 'beats_per_minute']
    }


def convert_to_standard_unit(value: float, current_unit: str, metric: str) -> tuple[float, str]:
    """
    Convert a value to the standard unit for the metric.
    
    Args:
        value: The numeric value
        current_unit: Current unit of the value
        metric: Metric type
        
    Returns:
        Tuple of (converted_value, standard_unit)
    """
    conversions = {
        'sleep': {
            'hours': (lambda x: x * 60, 'minutes'),
            'h': (lambda x: x * 60, 'minutes'),
            'minutes': (lambda x: x, 'minutes'),
            'min': (lambda x: x, 'minutes')
        },
        'weight': {
            'lbs': (lambda x: x * 0.453592, 'kg'),
            'pounds': (lambda x: x * 0.453592, 'kg'),
            'kg': (lambda x: x, 'kg'),
            'kilograms': (lambda x: x, 'kg')
        },
        'steps': {
            'steps': (lambda x: x, 'steps'),
            'count': (lambda x: x, 'steps')
        },
        'heart_rate': {
            'bpm': (lambda x: x, 'bpm'),
            'beats_per_minute': (lambda x: x, 'bpm')
        }
    }
    
    if metric not in conversions:
        return value, current_unit
    
    metric_conversions = conversions[metric]
    current_unit_lower = current_unit.lower()
    
    if current_unit_lower in metric_conversions:
        converter, standard_unit = metric_conversions[current_unit_lower]
        return converter(value), standard_unit
    
    # If no conversion found, return as-is
    return value, current_unit


def calculate_quality_score(points: List[Dict[str, Any]], metric: str) -> Optional[float]:
    """
    Calculate a quality score for the data points.
    Higher score indicates better data quality.
    
    Args:
        points: List of data points
        metric: Metric type
        
    Returns:
        Quality score between 0.0 and 1.0, or None if can't calculate
    """
    if not points:
        return None
    
    try:
        # Basic quality scoring based on data completeness and consistency
        total_points = len(points)
        
        # Check for complete data (no missing values)
        complete_points = sum(1 for p in points if p.get('value') is not None and p.get('start_time'))
        completeness_score = complete_points / total_points if total_points > 0 else 0
        
        # Check for reasonable value ranges (metric-specific)
        reasonable_points = 0
        for point in points:
            if _is_reasonable_value(point.get('value', 0), metric):
                reasonable_points += 1
        
        reasonableness_score = reasonable_points / total_points if total_points > 0 else 0
        
        # Combine scores (weighted average)
        quality_score = (completeness_score * 0.6) + (reasonableness_score * 0.4)
        
        return round(quality_score, 3)
        
    except Exception:
        return None


def _is_reasonable_value(value: float, metric: str) -> bool:
    """Check if a value is within reasonable bounds for the metric."""
    try:
        value = float(value)
        
        reasonable_ranges = {
            'steps': (0, 100000),  # 0 to 100k steps per day
            'sleep': (0, 1440),    # 0 to 24 hours in minutes
            'weight': (1, 1000),   # 1 to 1000 kg
            'heart_rate': (30, 250) # 30 to 250 bpm
        }
        
        if metric in reasonable_ranges:
            min_val, max_val = reasonable_ranges[metric]
            return min_val <= value <= max_val
        
        return True  # Default to true for unknown metrics
        
    except (ValueError, TypeError):
        return False