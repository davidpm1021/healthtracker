"""
Weight-specific logic for Health Tracker normalization.
Weight data is processed to select the most recent value per day, stored in kilograms.
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


class WeightProcessor(MetricProcessor):
    """Processor for weight data - selects most recent value per day."""
    
    def __init__(self):
        super().__init__("weight")
    
    def _is_valid_point(self, point: Dict[str, Any]) -> bool:
        """Validate weight-specific data point."""
        if not super()._is_valid_point(point):
            return False
        
        try:
            value = float(point['value'])
            
            # Weight should be positive and reasonable (1-1000 kg range)
            if value <= 0:
                self.logger.warning(f"Non-positive weight value: {value}")
                return False
            
            # Convert to kg for validation if needed
            unit = point.get('unit', '').lower()
            if unit in ['lbs', 'pounds']:
                value_kg = value * 0.453592
            else:
                value_kg = value
            
            if value_kg < 1 or value_kg > 1000:  # Reasonable weight range in kg
                self.logger.warning(f"Unrealistic weight value: {value_kg} kg")
                return False
            
            # Check unit is valid for weight
            if unit not in ['kg', 'kilograms', 'lbs', 'pounds']:
                self.logger.warning(f"Invalid weight unit: {unit}")
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
        Normalize weight data by selecting the most recent measurement for the day.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            points: List of raw weight data points for the day
            existing_summary: Existing daily summary if any
            
        Returns:
            DailySummary object with most recent weight for the day
        """
        if not points:
            return None
        
        try:
            # Validate and filter points
            valid_points = self.validate_points(points)
            
            if not valid_points:
                self.logger.warning(f"No valid weight points for {date_str}")
                return None
            
            # Process weight data and find most recent
            processed_weights = []
            
            for point in valid_points:
                try:
                    # Parse timestamp
                    clean_timestamp = point['start_time'].replace('Z', '+00:00')
                    timestamp = datetime.fromisoformat(clean_timestamp)
                    
                    # Convert to standard unit (kg)
                    value, standard_unit = convert_to_standard_unit(
                        float(point['value']), 
                        point['unit'], 
                        'weight'
                    )
                    
                    # Extract additional metadata if available
                    metadata = point.get('metadata', {})
                    body_fat = None
                    muscle_mass = None
                    
                    if isinstance(metadata, dict):
                        if 'body_fat_percentage' in metadata:
                            try:
                                body_fat = float(metadata['body_fat_percentage'])
                                if not (0 <= body_fat <= 100):
                                    body_fat = None
                            except (ValueError, TypeError):
                                pass
                        
                        if 'muscle_mass_kg' in metadata:
                            try:
                                muscle_mass = float(metadata['muscle_mass_kg'])
                                if muscle_mass <= 0:
                                    muscle_mass = None
                            except (ValueError, TypeError):
                                pass
                    
                    processed_weights.append({
                        'timestamp': timestamp,
                        'weight_kg': value,
                        'body_fat_percentage': body_fat,
                        'muscle_mass_kg': muscle_mass,
                        'original_point': point
                    })
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to process weight point: {e}")
                    continue
            
            if not processed_weights:
                self.logger.warning(f"No processable weight points for {date_str}")
                return None
            
            # Select most recent weight measurement
            most_recent_weight = max(processed_weights, key=lambda x: x['timestamp'])
            
            # Calculate data quality
            data_quality = calculate_quality_score([most_recent_weight['original_point']], 'weight')
            
            # Create daily summary
            summary = DailySummary(
                date=date_str,
                metric=MetricType.WEIGHT,
                value=round(most_recent_weight['weight_kg'], 2),  # Keep 2 decimal places
                unit='kg'
            )
            
            # Log the normalization
            measurement_time = most_recent_weight['timestamp'].strftime('%H:%M')
            additional_info = ""
            if most_recent_weight['body_fat_percentage']:
                additional_info += f", BF: {most_recent_weight['body_fat_percentage']:.1f}%"
            if most_recent_weight['muscle_mass_kg']:
                additional_info += f", MM: {most_recent_weight['muscle_mass_kg']:.1f}kg"
            
            self.logger.info(f"Selected weight for {date_str}: {most_recent_weight['weight_kg']:.2f}kg at {measurement_time}{additional_info} from {len(processed_weights)} measurements (quality: {data_quality})")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to normalize weight for {date_str}: {e}")
            return None


def normalize_weight(
    date_str: str, 
    points: List[Dict[str, Any]], 
    existing_summary: Optional[Dict[str, Any]] = None
) -> Optional[DailySummary]:
    """
    Convenience function to normalize weight data.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        points: List of raw weight data points
        existing_summary: Existing summary if any
        
    Returns:
        DailySummary object or None if normalization fails
    """
    processor = WeightProcessor()
    return processor.normalize(date_str, points, existing_summary)


def analyze_weight_patterns(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze patterns in weight data for insights.
    
    Args:
        points: List of weight data points
        
    Returns:
        Dictionary with weight pattern analysis
    """
    if not points:
        return {'error': 'No points provided'}
    
    try:
        weight_measurements = []
        
        for point in points:
            try:
                start_time_str = point['start_time']
                clean_start = start_time_str.replace('Z', '+00:00')
                start_time = datetime.fromisoformat(clean_start)
                
                # Convert to kg
                value, _ = convert_to_standard_unit(
                    float(point['value']), 
                    point['unit'], 
                    'weight'
                )
                
                # Extract additional metrics if available
                metadata = point.get('metadata', {})
                body_fat = None
                muscle_mass = None
                
                if isinstance(metadata, dict):
                    if 'body_fat_percentage' in metadata:
                        try:
                            body_fat = float(metadata['body_fat_percentage'])
                            if not (0 <= body_fat <= 100):
                                body_fat = None
                        except (ValueError, TypeError):
                            pass
                    
                    if 'muscle_mass_kg' in metadata:
                        try:
                            muscle_mass = float(metadata['muscle_mass_kg'])
                            if muscle_mass <= 0:
                                muscle_mass = None
                        except (ValueError, TypeError):
                            pass
                
                weight_measurements.append({
                    'timestamp': start_time,
                    'weight_kg': value,
                    'body_fat_percentage': body_fat,
                    'muscle_mass_kg': muscle_mass,
                    'hour': start_time.hour
                })
                
            except (ValueError, KeyError):
                continue
        
        if not weight_measurements:
            return {'error': 'No valid weight measurements'}
        
        # Sort by timestamp
        weight_measurements.sort(key=lambda x: x['timestamp'])
        
        # Calculate basic statistics
        weights = [m['weight_kg'] for m in weight_measurements]
        avg_weight = sum(weights) / len(weights) if weights else 0
        max_weight = max(weights) if weights else 0
        min_weight = min(weights) if weights else 0
        weight_range = max_weight - min_weight
        
        # Calculate weight trend (simple linear)
        if len(weight_measurements) >= 2:
            first_weight = weight_measurements[0]['weight_kg']
            last_weight = weight_measurements[-1]['weight_kg']
            weight_change = last_weight - first_weight
            
            # Calculate days between measurements
            time_span = weight_measurements[-1]['timestamp'] - weight_measurements[0]['timestamp']
            days_span = time_span.days if time_span.days > 0 else 1
            weight_change_per_day = weight_change / days_span
        else:
            weight_change = 0
            weight_change_per_day = 0
        
        # Analyze measurement times
        measurement_hours = [m['hour'] for m in weight_measurements]
        most_common_hour = max(set(measurement_hours), key=measurement_hours.count) if measurement_hours else None
        
        # Body composition statistics if available
        body_fat_measurements = [m['body_fat_percentage'] for m in weight_measurements if m['body_fat_percentage'] is not None]
        muscle_mass_measurements = [m['muscle_mass_kg'] for m in weight_measurements if m['muscle_mass_kg'] is not None]
        
        avg_body_fat = sum(body_fat_measurements) / len(body_fat_measurements) if body_fat_measurements else None
        avg_muscle_mass = sum(muscle_mass_measurements) / len(muscle_mass_measurements) if muscle_mass_measurements else None
        
        # Weight stability analysis
        if len(weights) > 1:
            weight_std = (sum((w - avg_weight) ** 2 for w in weights) / len(weights)) ** 0.5
            weight_cv = weight_std / avg_weight if avg_weight > 0 else 0
        else:
            weight_std = 0
            weight_cv = 0
        
        result = {
            'total_measurements': len(weight_measurements),
            'avg_weight_kg': round(avg_weight, 2),
            'max_weight_kg': round(max_weight, 2),
            'min_weight_kg': round(min_weight, 2),
            'weight_range_kg': round(weight_range, 2),
            'weight_change_kg': round(weight_change, 2),
            'weight_change_per_day_kg': round(weight_change_per_day, 3),
            'weight_stability': round(weight_cv, 3),  # Lower = more stable
            'most_common_measurement_hour': most_common_hour
        }
        
        # Add body composition if available
        if avg_body_fat is not None:
            result['avg_body_fat_percentage'] = round(avg_body_fat, 1)
            result['body_fat_measurements_count'] = len(body_fat_measurements)
        
        if avg_muscle_mass is not None:
            result['avg_muscle_mass_kg'] = round(avg_muscle_mass, 2)
            result['muscle_mass_measurements_count'] = len(muscle_mass_measurements)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze weight patterns: {e}")
        return {'error': str(e)}