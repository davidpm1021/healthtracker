"""
Steps-specific logic for Health Tracker normalization.
Steps are summed per day to get daily totals.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import DailySummary, MetricType
from metrics import MetricProcessor, convert_to_standard_unit, calculate_quality_score

# Set up logging
logger = logging.getLogger(__name__)


class StepsProcessor(MetricProcessor):
    """Processor for steps data - sums steps per day."""
    
    def __init__(self):
        super().__init__("steps")
    
    def _is_valid_point(self, point: Dict[str, Any]) -> bool:
        """Validate steps-specific data point."""
        if not super()._is_valid_point(point):
            return False
        
        try:
            value = float(point['value'])
            
            # Steps should be non-negative and reasonable
            if value < 0:
                self.logger.warning(f"Negative steps value: {value}")
                return False
            
            if value > 100000:  # More than 100k steps seems unrealistic
                self.logger.warning(f"Unrealistic steps value: {value}")
                return False
            
            # Check unit is valid for steps
            unit = point.get('unit', '').lower()
            if unit not in ['steps', 'count']:
                self.logger.warning(f"Invalid steps unit: {unit}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def normalize(
        self, 
        date_str: str, 
        points: List[Dict[str, Any]], 
        existing_summary: Optional[Dict[str, Any]] = None
    ) -> Optional[DailySummary]:
        """
        Normalize steps data by summing all step counts for the day.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            points: List of raw step data points for the day
            existing_summary: Existing daily summary if any
            
        Returns:
            DailySummary object with total steps for the day
        """
        if not points:
            return None
        
        try:
            # Validate and filter points
            valid_points = self.validate_points(points)
            
            if not valid_points:
                self.logger.warning(f"No valid steps points for {date_str}")
                return None
            
            # Sum all steps for the day
            total_steps = 0
            processed_points = []
            
            for point in valid_points:
                try:
                    # Convert to standard unit (steps)
                    value, standard_unit = convert_to_standard_unit(
                        float(point['value']), 
                        point['unit'], 
                        'steps'
                    )
                    
                    total_steps += value
                    processed_points.append({**point, 'normalized_value': value})
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to process steps point: {e}")
                    continue
            
            if total_steps <= 0:
                self.logger.warning(f"Total steps is zero or negative for {date_str}")
                return None
            
            # Calculate quality score
            quality_score = calculate_quality_score(processed_points, 'steps')
            
            # Create daily summary
            summary = DailySummary(
                date=date_str,
                metric=MetricType.STEPS,
                value=round(total_steps),  # Steps should be whole numbers
                unit='steps'
            )
            
            # Log the normalization
            self.logger.info(f"Normalized {len(valid_points)} steps points for {date_str}: {total_steps} steps (quality: {quality_score})")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to normalize steps for {date_str}: {e}")
            return None


def normalize_steps(
    date_str: str, 
    points: List[Dict[str, Any]], 
    existing_summary: Optional[Dict[str, Any]] = None
) -> Optional[DailySummary]:
    """
    Convenience function to normalize steps data.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        points: List of raw step data points
        existing_summary: Existing summary if any
        
    Returns:
        DailySummary object or None if normalization fails
    """
    processor = StepsProcessor()
    return processor.normalize(date_str, points, existing_summary)


def analyze_steps_patterns(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze patterns in steps data for insights.
    
    Args:
        points: List of steps data points
        
    Returns:
        Dictionary with pattern analysis
    """
    if not points:
        return {'error': 'No points provided'}
    
    try:
        # Extract timestamps and values
        timestamped_values = []
        
        for point in points:
            try:
                timestamp_str = point['start_time']
                # Handle timezone suffixes
                clean_timestamp = timestamp_str.replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(clean_timestamp)
                value = float(point['value'])
                
                timestamped_values.append((timestamp, value))
                
            except (ValueError, KeyError):
                continue
        
        if not timestamped_values:
            return {'error': 'No valid timestamped points'}
        
        # Sort by timestamp
        timestamped_values.sort(key=lambda x: x[0])
        
        # Calculate patterns
        total_steps = sum(value for _, value in timestamped_values)
        avg_steps_per_reading = total_steps / len(timestamped_values) if timestamped_values else 0
        
        # Find peak activity periods (hour of day)
        hourly_totals = {}
        for timestamp, value in timestamped_values:
            hour = timestamp.hour
            hourly_totals[hour] = hourly_totals.get(hour, 0) + value
        
        peak_hour = max(hourly_totals.items(), key=lambda x: x[1])[0] if hourly_totals else None
        
        # Calculate activity distribution
        if len(timestamped_values) > 1:
            time_span_hours = (timestamped_values[-1][0] - timestamped_values[0][0]).total_seconds() / 3600
            avg_steps_per_hour = total_steps / time_span_hours if time_span_hours > 0 else 0
        else:
            time_span_hours = 0
            avg_steps_per_hour = 0
        
        return {
            'total_steps': total_steps,
            'data_points': len(timestamped_values),
            'avg_steps_per_reading': round(avg_steps_per_reading, 1),
            'avg_steps_per_hour': round(avg_steps_per_hour, 1),
            'peak_activity_hour': peak_hour,
            'time_span_hours': round(time_span_hours, 2),
            'hourly_distribution': dict(sorted(hourly_totals.items()))
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze steps patterns: {e}")
        return {'error': str(e)}