"""
Heart rate-specific logic for Health Tracker normalization.
Heart rate uses the average of all readings per day.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models import DailySummary, MetricType

# Set up logging
logger = logging.getLogger(__name__)


def normalize_heart_rate(date_str: str, points: List[Dict[str, Any]], existing_summary: Optional[Dict[str, Any]] = None) -> Optional[DailySummary]:
    """
    Normalize heart rate data for a single day.
    Uses the average of all heart rate readings.
    """
    try:
        if not points:
            return None
            
        # Calculate average heart rate
        values = [float(point.get('value', 0)) for point in points if point.get('value', 0) > 0]
        if not values:
            return None
            
        avg_hr = sum(values) / len(values)
        
        # Create daily summary
        summary = DailySummary(
            date=date_str,
            metric=MetricType.HEART_RATE,
            value=round(avg_hr, 1),
            unit='bpm'
        )
        
        logger.debug(f"Normalized heart rate for {date_str}: {avg_hr:.1f} bpm from {len(points)} points")
        return summary
        
    except Exception as e:
        logger.error(f"Error normalizing heart rate for {date_str}: {e}")
        return None