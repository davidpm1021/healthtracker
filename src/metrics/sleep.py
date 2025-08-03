"""
Sleep-specific logic for Health Tracker normalization.
Sleep data is aggregated into total asleep minutes per night, plus quality if available.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, time, timedelta
import logging

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import DailySummary, MetricType
from metrics import MetricProcessor, convert_to_standard_unit, calculate_quality_score

# Set up logging
logger = logging.getLogger(__name__)


class SleepProcessor(MetricProcessor):
    """Processor for sleep data - aggregates total sleep time and quality."""
    
    def __init__(self):
        super().__init__("sleep")
    
    def _is_valid_point(self, point: Dict[str, Any]) -> bool:
        """Validate sleep-specific data point."""
        if not super()._is_valid_point(point):
            return False
        
        try:
            value = float(point['value'])
            
            # Sleep should be non-negative and reasonable (max 24 hours)
            if value < 0:
                self.logger.warning(f"Negative sleep value: {value}")
                return False
            
            # Convert to minutes for validation
            unit = point.get('unit', '').lower()
            if unit in ['hours', 'h']:
                value_minutes = value * 60
            else:
                value_minutes = value
            
            if value_minutes > 1440:  # More than 24 hours
                self.logger.warning(f"Unrealistic sleep value: {value_minutes} minutes")
                return False
            
            # Check unit is valid for sleep
            if unit not in ['minutes', 'min', 'hours', 'h']:
                self.logger.warning(f"Invalid sleep unit: {unit}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def _determine_sleep_date(self, start_time: str, end_time: Optional[str] = None) -> str:
        """
        Determine which date to assign sleep data to.
        Sleep that starts after 6 PM is assigned to the same day.
        Sleep that starts before 6 AM is assigned to the previous day.
        
        Args:
            start_time: Sleep start timestamp
            end_time: Sleep end timestamp (optional)
            
        Returns:
            Date string in YYYY-MM-DD format
        """
        try:
            # Parse start time
            clean_timestamp = start_time.replace('Z', '+00:00')
            start_dt = datetime.fromisoformat(clean_timestamp)
            
            # If sleep starts after 6 PM (18:00), assign to same date
            # If sleep starts before 6 AM (06:00), assign to previous date
            # Otherwise, assign to same date
            
            if start_dt.time() >= time(18, 0):  # After 6 PM
                sleep_date = start_dt.date()
            elif start_dt.time() < time(6, 0):  # Before 6 AM
                sleep_date = start_dt.date() - timedelta(days=1)
            else:
                sleep_date = start_dt.date()
            
            return sleep_date.isoformat()
            
        except (ValueError, AttributeError):
            # Fallback to using the date from start_time
            try:
                clean_timestamp = start_time.replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_timestamp)
                return dt.date().isoformat()
            except:
                logger.error(f"Cannot parse sleep timestamp: {start_time}")
                return datetime.now().date().isoformat()
    
    def normalize(
        self, 
        date_str: str, 
        points: List[Dict[str, Any]], 
        existing_summary: Optional[Dict[str, Any]] = None
    ) -> Optional[DailySummary]:
        """
        Normalize sleep data by aggregating total sleep time for the night.
        
        Args:
            date_str: Date string in YYYY-MM-DD format (sleep date, not necessarily start time date)
            points: List of raw sleep data points
            existing_summary: Existing daily summary if any
            
        Returns:
            DailySummary object with total sleep minutes
        """
        if not points:
            return None
        
        try:
            # Validate and filter points
            valid_points = self.validate_points(points)
            
            if not valid_points:
                self.logger.warning(f"No valid sleep points for {date_str}")
                return None
            
            # Process sleep data
            total_sleep_minutes = 0
            processed_points = []
            sleep_quality_scores = []
            
            for point in valid_points:
                try:
                    # Convert to standard unit (minutes)
                    value, standard_unit = convert_to_standard_unit(
                        float(point['value']), 
                        point['unit'], 
                        'sleep'
                    )
                    
                    # Determine if this point should be included based on sleep date logic
                    actual_sleep_date = self._determine_sleep_date(
                        point['start_time'], 
                        point.get('end_time')
                    )
                    
                    # Only include points that belong to this sleep date
                    if actual_sleep_date == date_str:
                        total_sleep_minutes += value
                        processed_points.append({**point, 'normalized_value': value})
                        
                        # Extract quality score if available in metadata
                        metadata = point.get('metadata', {})
                        if isinstance(metadata, dict) and 'quality' in metadata:
                            try:
                                quality = float(metadata['quality'])
                                if 0 <= quality <= 1:
                                    sleep_quality_scores.append(quality)
                            except (ValueError, TypeError):
                                pass
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to process sleep point: {e}")
                    continue
            
            if total_sleep_minutes <= 0:
                self.logger.warning(f"Total sleep is zero or negative for {date_str}")
                return None
            
            # Calculate average quality score if available
            avg_quality = None
            if sleep_quality_scores:
                avg_quality = round(sum(sleep_quality_scores) / len(sleep_quality_scores), 3)
            
            # Calculate overall data quality score
            data_quality = calculate_quality_score(processed_points, 'sleep')
            
            # Create daily summary
            summary = DailySummary(
                date=date_str,
                metric=MetricType.SLEEP,
                value=round(total_sleep_minutes, 1),  # Keep one decimal for precision
                unit='minutes'
            )
            
            # Log the normalization
            quality_info = f", quality: {avg_quality}" if avg_quality else ""
            self.logger.info(f"Normalized {len(processed_points)} sleep points for {date_str}: {total_sleep_minutes} minutes{quality_info} (data quality: {data_quality})")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to normalize sleep for {date_str}: {e}")
            return None


def normalize_sleep(
    date_str: str, 
    points: List[Dict[str, Any]], 
    existing_summary: Optional[Dict[str, Any]] = None
) -> Optional[DailySummary]:
    """
    Convenience function to normalize sleep data.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        points: List of raw sleep data points
        existing_summary: Existing summary if any
        
    Returns:
        DailySummary object or None if normalization fails
    """
    processor = SleepProcessor()
    return processor.normalize(date_str, points, existing_summary)


def analyze_sleep_patterns(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze patterns in sleep data for insights.
    
    Args:
        points: List of sleep data points
        
    Returns:
        Dictionary with sleep pattern analysis
    """
    if not points:
        return {'error': 'No points provided'}
    
    try:
        sleep_sessions = []
        
        for point in points:
            try:
                start_time_str = point['start_time']
                clean_start = start_time_str.replace('Z', '+00:00')
                start_time = datetime.fromisoformat(clean_start)
                
                # Try to get end time if available
                end_time = None
                if 'end_time' in point and point['end_time']:
                    clean_end = point['end_time'].replace('Z', '+00:00')
                    end_time = datetime.fromisoformat(clean_end)
                
                # Convert duration to minutes
                value, _ = convert_to_standard_unit(
                    float(point['value']), 
                    point['unit'], 
                    'sleep'
                )
                
                sleep_sessions.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': value,
                    'start_hour': start_time.hour
                })
                
            except (ValueError, KeyError):
                continue
        
        if not sleep_sessions:
            return {'error': 'No valid sleep sessions'}
        
        # Sort by start time
        sleep_sessions.sort(key=lambda x: x['start_time'])
        
        # Calculate patterns
        total_sleep = sum(session['duration_minutes'] for session in sleep_sessions)
        avg_sleep_duration = total_sleep / len(sleep_sessions) if sleep_sessions else 0
        
        # Find common bedtimes (start hours)
        bedtime_hours = [session['start_hour'] for session in sleep_sessions]
        most_common_bedtime = max(set(bedtime_hours), key=bedtime_hours.count) if bedtime_hours else None
        
        # Calculate sleep efficiency metrics
        longest_session = max(session['duration_minutes'] for session in sleep_sessions) if sleep_sessions else 0
        shortest_session = min(session['duration_minutes'] for session in sleep_sessions) if sleep_sessions else 0
        
        # Categorize sleep quality based on duration
        sleep_quality_categories = {
            'excellent': 0,  # 7-9 hours
            'good': 0,       # 6-7 or 9-10 hours  
            'fair': 0,       # 5-6 or 10-11 hours
            'poor': 0        # <5 or >11 hours
        }
        
        for session in sleep_sessions:
            minutes = session['duration_minutes']
            hours = minutes / 60
            
            if 7 <= hours <= 9:
                sleep_quality_categories['excellent'] += 1
            elif (6 <= hours < 7) or (9 < hours <= 10):
                sleep_quality_categories['good'] += 1
            elif (5 <= hours < 6) or (10 < hours <= 11):
                sleep_quality_categories['fair'] += 1
            else:
                sleep_quality_categories['poor'] += 1
        
        return {
            'total_sessions': len(sleep_sessions),
            'total_sleep_hours': round(total_sleep / 60, 2),
            'avg_sleep_hours': round(avg_sleep_duration / 60, 2),
            'longest_session_hours': round(longest_session / 60, 2),
            'shortest_session_hours': round(shortest_session / 60, 2),
            'most_common_bedtime_hour': most_common_bedtime,
            'sleep_quality_distribution': sleep_quality_categories
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze sleep patterns: {e}")
        return {'error': str(e)}