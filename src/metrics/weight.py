"""
Weight-specific logic for Health Tracker normalization.
Weight uses the most recent measurement per day.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models import DailySummary, MetricType

# Set up logging
logger = logging.getLogger(__name__)


def normalize_weight(date_str: str, points: List[Dict[str, Any]], existing_summary: Optional[Dict[str, Any]] = None) -> Optional[DailySummary]:
    """
    Normalize weight data for a single day.
    Uses the most recent weight measurement.
    """
    try:
        if not points:
            return None
            
        # Sort by timestamp and get the most recent
        sorted_points = sorted(points, key=lambda p: p.get('start_time', ''))
        latest_point = sorted_points[-1]
        weight_value = float(latest_point.get('value', 0))
        
        if weight_value <= 0:
            return None
            
        # Create daily summary
        summary = DailySummary(
            date=date_str,
            metric=MetricType.WEIGHT,
            value=weight_value,
            unit='kg'
        )
        
        logger.debug(f"Normalized weight for {date_str}: {weight_value} kg from {len(points)} points")
        return summary
        
    except Exception as e:
        logger.error(f"Error normalizing weight for {date_str}: {e}")
        return None