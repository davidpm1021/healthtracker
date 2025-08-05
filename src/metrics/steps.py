"""
Steps-specific logic for Health Tracker normalization.
Steps are summed per day to get daily totals.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models import DailySummary, MetricType

# Set up logging
logger = logging.getLogger(__name__)


def normalize_steps(date_str: str, points: List[Dict[str, Any]], existing_summary: Optional[Dict[str, Any]] = None) -> Optional[DailySummary]:
    """
    Normalize steps data for a single day.
    Steps are summed across all time periods.
    """
    try:
        if not points:
            return None
            
        # Sum all step counts for the day
        total_steps = sum(float(point.get('value', 0)) for point in points)
        
        if total_steps <= 0:
            return None
            
        # Create daily summary
        summary = DailySummary(
            date=date_str,
            metric=MetricType.STEPS,
            value=total_steps,
            unit='steps'
        )
        
        logger.debug(f"Normalized steps for {date_str}: {total_steps} steps from {len(points)} points")
        return summary
        
    except Exception as e:
        logger.error(f"Error normalizing steps for {date_str}: {e}")
        return None