"""
Sleep-specific logic for Health Tracker normalization.
Sleep data is processed to get total sleep duration per night.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models import DailySummary, MetricType

# Set up logging
logger = logging.getLogger(__name__)


def normalize_sleep(date_str: str, points: List[Dict[str, Any]], existing_summary: Optional[Dict[str, Any]] = None) -> Optional[DailySummary]:
    """
    Normalize sleep data for a single day.
    Uses the total sleep duration from the latest/longest session.
    """
    try:
        if not points:
            return None
            
        # Get the longest sleep session (in case of multiple)
        max_sleep = max(float(point.get('value', 0)) for point in points)
        
        if max_sleep <= 0:
            return None
            
        # Create daily summary
        summary = DailySummary(
            date=date_str,
            metric=MetricType.SLEEP,
            value=max_sleep,
            unit='minutes'
        )
        
        logger.debug(f"Normalized sleep for {date_str}: {max_sleep} minutes from {len(points)} points")
        return summary
        
    except Exception as e:
        logger.error(f"Error normalizing sleep for {date_str}: {e}")
        return None