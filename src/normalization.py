"""
Core normalization functions for Health Tracker.
Handles transformation of raw health data points into daily summaries.
"""
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
import logging

from .models import RawPoint, DailySummary, MetricType
from .database import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Custom exception for normalization errors."""
    pass


def parse_iso_date(iso_timestamp: str) -> date:
    """
    Parse ISO timestamp and return date.
    
    Args:
        iso_timestamp: ISO format timestamp string
        
    Returns:
        date object
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        # Handle timezone suffixes
        clean_timestamp = iso_timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_timestamp)
        return dt.date()
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid timestamp format: {iso_timestamp}") from e


def group_raw_points_by_date_and_metric(raw_points: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    Group raw data points by date and metric type.
    
    Args:
        raw_points: List of raw data point dictionaries
        
    Returns:
        Dictionary with (date_str, metric) tuples as keys and lists of raw points as values
    """
    grouped = defaultdict(list)
    
    for point in raw_points:
        try:
            point_date = parse_iso_date(point['start_time'])
            date_str = point_date.isoformat()
            metric = point['metric']
            grouped[(date_str, metric)].append(point)
        except (ValueError, KeyError) as e:
            logger.warning(f"Skipping invalid raw point: {e}")
            continue
    
    return dict(grouped)


def validate_raw_point(point: Dict[str, Any]) -> bool:
    """
    Validate that a raw data point has required fields and valid values.
    
    Args:
        point: Raw data point dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['metric', 'start_time', 'value', 'unit', 'source']
    
    # Check required fields
    for field in required_fields:
        if field not in point:
            logger.warning(f"Raw point missing required field: {field}")
            return False
    
    # Check value is numeric and non-negative
    try:
        value = float(point['value'])
        if value < 0:
            logger.warning(f"Raw point has negative value: {value}")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Raw point has invalid value: {point['value']}")
        return False
    
    # Check metric is valid
    if point['metric'] not in [MetricType.STEPS, MetricType.SLEEP, MetricType.WEIGHT, MetricType.HEART_RATE]:
        logger.warning(f"Raw point has invalid metric: {point['metric']}")
        return False
    
    return True


def filter_and_deduplicate_raw_points(raw_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out invalid points and remove duplicates.
    
    Args:
        raw_points: List of raw data point dictionaries
        
    Returns:
        Filtered and deduplicated list of raw points
    """
    # Filter valid points
    valid_points = [point for point in raw_points if validate_raw_point(point)]
    
    # Deduplicate based on metric, start_time, and source
    seen_keys = set()
    deduplicated_points = []
    
    for point in valid_points:
        key = (point['metric'], point['start_time'], point['source'])
        if key not in seen_keys:
            seen_keys.add(key)
            deduplicated_points.append(point)
        else:
            logger.debug(f"Removing duplicate point: {key}")
    
    logger.info(f"Filtered {len(raw_points)} raw points to {len(deduplicated_points)} valid unique points")
    return deduplicated_points


def normalize_raw_points_to_summaries(
    raw_points: List[Dict[str, Any]], 
    existing_summaries: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None
) -> List[DailySummary]:
    """
    Normalize raw data points into daily summaries.
    
    Args:
        raw_points: List of raw data point dictionaries
        existing_summaries: Optional dict of existing summaries keyed by (date, metric)
        
    Returns:
        List of DailySummary objects
    """
    if not raw_points:
        return []
    
    # Filter and deduplicate points
    clean_points = filter_and_deduplicate_raw_points(raw_points)
    if not clean_points:
        logger.warning("No valid raw points to normalize")
        return []
    
    # Group by date and metric
    grouped_points = group_raw_points_by_date_and_metric(clean_points)
    
    summaries = []
    
    for (date_str, metric), points in grouped_points.items():
        try:
            # Import metric-specific processors
            from .metrics.steps import normalize_steps
            from .metrics.sleep import normalize_sleep  
            from .metrics.weight import normalize_weight
            from .metrics.heart_rate import normalize_heart_rate
            
            # Get existing summary if available
            existing_summary = None
            if existing_summaries and (date_str, metric) in existing_summaries:
                existing_summary = existing_summaries[(date_str, metric)]
            
            # Normalize based on metric type
            if metric == MetricType.STEPS:
                summary = normalize_steps(date_str, points, existing_summary)
            elif metric == MetricType.SLEEP:
                summary = normalize_sleep(date_str, points, existing_summary)
            elif metric == MetricType.WEIGHT:
                summary = normalize_weight(date_str, points, existing_summary)
            elif metric == MetricType.HEART_RATE:
                summary = normalize_heart_rate(date_str, points, existing_summary)
            else:
                logger.warning(f"Unknown metric type for normalization: {metric}")
                continue
            
            if summary:
                summaries.append(summary)
                logger.debug(f"Normalized {len(points)} {metric} points for {date_str} -> {summary.value}")
            
        except Exception as e:
            logger.error(f"Failed to normalize {metric} for {date_str}: {e}")
            continue
    
    logger.info(f"Generated {len(summaries)} daily summaries from {len(clean_points)} raw points")
    return summaries


def get_recent_raw_points_for_normalization(
    db_manager: DatabaseManager, 
    days_back: int = 7,
    specific_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent raw points that need normalization.
    
    Args:
        db_manager: Database manager instance
        days_back: Number of days back to look for raw points
        specific_date: If provided, only get points for this specific date
        
    Returns:
        List of raw point dictionaries
    """
    try:
        if specific_date:
            # Get points for specific date
            start_date = specific_date
            end_date = specific_date
        else:
            # Get points for last N days
            from datetime import datetime, timedelta
            end_date = datetime.now().date().isoformat()
            start_date = (datetime.now().date() - timedelta(days=days_back)).isoformat()
        
        all_raw_points = []
        
        # Get raw points for each metric type
        for metric in [MetricType.STEPS, MetricType.SLEEP, MetricType.WEIGHT, MetricType.HEART_RATE]:
            points = db_manager.get_raw_points(metric, start_date, end_date)
            all_raw_points.extend(points)
        
        logger.info(f"Retrieved {len(all_raw_points)} raw points for normalization (date range: {start_date} to {end_date})")
        return all_raw_points
        
    except Exception as e:
        logger.error(f"Failed to retrieve raw points for normalization: {e}")
        return []


def get_existing_summaries(
    db_manager: DatabaseManager,
    date_range: Tuple[str, str]
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Get existing daily summaries for the given date range.
    
    Args:
        db_manager: Database manager instance
        date_range: Tuple of (start_date, end_date) strings
        
    Returns:
        Dictionary keyed by (date, metric) with existing summary data
    """
    try:
        start_date, end_date = date_range
        existing_summaries = {}
        
        # Get existing summaries for each metric
        for metric in [MetricType.STEPS, MetricType.SLEEP, MetricType.WEIGHT, MetricType.HEART_RATE]:
            summaries = db_manager.get_daily_summaries(metric, start_date, end_date)
            for summary in summaries:
                key = (summary['date'], summary['metric'])
                existing_summaries[key] = summary
        
        logger.debug(f"Retrieved {len(existing_summaries)} existing summaries for update")
        return existing_summaries
        
    except Exception as e:
        logger.error(f"Failed to retrieve existing summaries: {e}")
        return {}


def process_raw_data_to_summaries(
    db_manager: DatabaseManager,
    days_back: int = 7,
    specific_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function to process raw data into daily summaries.
    
    Args:
        db_manager: Database manager instance
        days_back: Number of days back to process
        specific_date: If provided, only process this specific date
        
    Returns:
        Dictionary with processing statistics
    """
    start_time = datetime.now()
    
    try:
        # Get raw points for processing
        raw_points = get_recent_raw_points_for_normalization(db_manager, days_back, specific_date)
        
        if not raw_points:
            logger.info("No raw points found for normalization")
            return {
                'success': True,
                'processed_points': 0,
                'generated_summaries': 0,
                'updated_summaries': 0,
                'processing_time_seconds': 0,
                'message': 'No raw points to process'
            }
        
        # Determine date range for existing summaries
        if specific_date:
            date_range = (specific_date, specific_date)
        else:
            from datetime import datetime, timedelta
            end_date = datetime.now().date().isoformat()
            start_date = (datetime.now().date() - timedelta(days=days_back)).isoformat()
            date_range = (start_date, end_date)
        
        # Get existing summaries
        existing_summaries = get_existing_summaries(db_manager, date_range)
        
        # Normalize raw points to summaries
        new_summaries = normalize_raw_points_to_summaries(raw_points, existing_summaries)
        
        # Update database with new summaries
        updated_count = 0
        generated_count = 0
        
        for summary in new_summaries:
            key = (summary.date, summary.metric)
            if key in existing_summaries:
                updated_count += 1
            else:
                generated_count += 1
            
            # Upsert summary
            db_manager.upsert_daily_summary(summary)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': True,
            'processed_points': len(raw_points),
            'generated_summaries': generated_count,
            'updated_summaries': updated_count,
            'processing_time_seconds': round(processing_time, 2),
            'message': f'Successfully processed {len(raw_points)} raw points into {len(new_summaries)} summaries'
        }
        
        logger.info(f"Normalization complete: {result['message']} in {processing_time:.2f}s")
        return result
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Normalization failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'processed_points': 0,
            'generated_summaries': 0,
            'updated_summaries': 0,
            'processing_time_seconds': round(processing_time, 2),
            'error': error_msg
        }