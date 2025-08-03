"""
Daily summary computation for Health Tracker.
Handles automated generation of daily summaries from raw data and computation of moving averages.
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from models import DailySummary, MetricType
from database import DatabaseManager
from normalization import normalize_raw_points_to_summaries

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummaryComputer:
    """Handles computation of daily summaries and related analytics."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize summary computer with database manager."""
        self.db = db_manager or DatabaseManager()
    
    def compute_daily_summaries(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        force_recompute: bool = False
    ) -> Dict[str, Any]:
        """
        Compute daily summaries for the specified date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
            end_date: End date in YYYY-MM-DD format (default: today)
            force_recompute: If True, recompute existing summaries
            
        Returns:
            Dictionary with computation results and statistics
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = date.today().isoformat()
            if not start_date:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            
            logger.info(f"Computing daily summaries from {start_date} to {end_date}")
            
            # Get raw data for the date range
            raw_data = self._get_raw_data_for_range(start_date, end_date)
            
            if not raw_data:
                logger.warning("No raw data found for the specified date range")
                return {
                    'success': True,
                    'message': 'No raw data to process',
                    'summaries_created': 0,
                    'summaries_updated': 0,
                    'date_range': (start_date, end_date)
                }
            
            # Get existing summaries if not force recomputing
            existing_summaries = {}
            if not force_recompute:
                existing_summaries = self._get_existing_summaries(start_date, end_date)
            
            # Normalize raw data to summaries
            new_summaries = normalize_raw_points_to_summaries(raw_data, existing_summaries)
            
            # Store summaries in database
            summaries_created = 0
            summaries_updated = 0
            
            for summary in new_summaries:
                summary_id = self.db.upsert_daily_summary(summary)
                if summary_id:
                    # Check if this was an update or create
                    key = (summary.date, summary.metric)
                    if key in existing_summaries:
                        summaries_updated += 1
                    else:
                        summaries_created += 1
            
            logger.info(f"Summary computation complete: {summaries_created} created, {summaries_updated} updated")
            
            return {
                'success': True,
                'summaries_created': summaries_created,
                'summaries_updated': summaries_updated,
                'total_summaries': len(new_summaries),
                'date_range': (start_date, end_date),
                'raw_points_processed': len(raw_data)
            }
            
        except Exception as e:
            logger.error(f"Error computing daily summaries: {e}")
            return {
                'success': False,
                'error': str(e),
                'summaries_created': 0,
                'summaries_updated': 0
            }
    
    def _get_raw_data_for_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get all raw data points for the specified date range."""
        raw_data = []
        
        # Get data for each automated metric
        for metric in MetricType.all():
            metric_data = self.db.get_raw_points(metric, start_date + 'T00:00:00Z', end_date + 'T23:59:59Z')
            raw_data.extend(metric_data)
        
        return raw_data
    
    def _get_existing_summaries(self, start_date: str, end_date: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Get existing daily summaries for the date range."""
        existing = {}
        
        summaries = self.db.get_daily_summaries_range(start_date, end_date)
        
        for summary in summaries:
            key = (summary['date'], summary['metric'])
            existing[key] = summary
        
        return existing
    
    def compute_moving_averages_and_trends(
        self, 
        metric: str, 
        end_date: Optional[str] = None,
        days_back: int = 60
    ) -> Dict[str, Any]:
        """
        Compute moving averages and trend slopes for a specific metric.
        
        Args:
            metric: Metric type to compute for
            end_date: End date for computation (default: today)
            days_back: How many days back to consider for computation
            
        Returns:
            Dictionary with moving averages and trend data
        """
        try:
            if not end_date:
                end_date = date.today().isoformat()
            
            start_date = (datetime.fromisoformat(end_date) - timedelta(days=days_back)).date().isoformat()
            
            # Get summaries for the metric
            summaries = self.db.get_daily_summaries_for_metric(metric, start_date, end_date)
            
            if len(summaries) < 2:
                logger.warning(f"Insufficient data for {metric} moving averages (need at least 2 points)")
                return {
                    'metric': metric,
                    'end_date': end_date,
                    'data_points': len(summaries),
                    'updated_summaries': 0,
                    'latest_values': None
                }
            
            # Sort by date
            summaries.sort(key=lambda x: x['date'])
            
            # Compute moving averages for each day
            updated_summaries = []
            
            for i, summary in enumerate(summaries):
                current_date = summary['date']
                current_value = summary['value']
                
                # Compute 7-day moving average
                avg_7day = self._compute_moving_average(summaries, i, 7)
                
                # Compute 30-day moving average  
                avg_30day = self._compute_moving_average(summaries, i, 30)
                
                # Compute trend slope (based on last 14 days)
                trend_slope = self._compute_trend_slope(summaries, i, 14)
                
                # Update summary with computed values
                updated_summary = DailySummary(
                    date=summary['date'],
                    metric=summary['metric'],
                    value=summary['value'],
                    unit=summary['unit'],
                    avg_7day=avg_7day,
                    avg_30day=avg_30day,
                    trend_slope=trend_slope,
                    id=summary.get('id'),
                    created_at=summary.get('created_at'),
                    updated_at=datetime.now().isoformat()
                )
                
                # Store updated summary
                self.db.upsert_daily_summary(updated_summary)
                updated_summaries.append(updated_summary)
            
            logger.info(f"Updated moving averages and trends for {len(updated_summaries)} {metric} summaries")
            
            # Return summary statistics
            latest_summary = updated_summaries[-1] if updated_summaries else None
            
            return {
                'metric': metric,
                'end_date': end_date,
                'data_points': len(summaries),
                'updated_summaries': len(updated_summaries),
                'latest_values': {
                    'value': latest_summary.value if latest_summary else None,
                    'avg_7day': latest_summary.avg_7day if latest_summary else None,
                    'avg_30day': latest_summary.avg_30day if latest_summary else None,
                    'trend_slope': latest_summary.trend_slope if latest_summary else None
                } if latest_summary else None
            }
            
        except Exception as e:
            logger.error(f"Error computing moving averages for {metric}: {e}")
            return {
                'metric': metric,
                'error': str(e),
                'data_points': 0,
                'updated_summaries': 0
            }
    
    def _compute_moving_average(self, summaries: List[Dict[str, Any]], current_index: int, window_days: int) -> Optional[float]:
        """Compute moving average for a specific window."""
        if current_index < 0:
            return None
        
        # Get the window of data points (going backwards from current)
        start_index = max(0, current_index - window_days + 1)
        window_data = summaries[start_index:current_index + 1]
        
        if not window_data:
            return None
        
        # Calculate average
        total_value = sum(s['value'] for s in window_data)
        return round(total_value / len(window_data), 2)
    
    def _compute_trend_slope(self, summaries: List[Dict[str, Any]], current_index: int, window_days: int) -> Optional[float]:
        """
        Compute trend slope using simple linear regression over the specified window.
        Returns slope value (positive = increasing, negative = decreasing, ~0 = flat).
        """
        if current_index < 1:  # Need at least 2 points
            return None
        
        # Get the window of data points
        start_index = max(0, current_index - window_days + 1)
        window_data = summaries[start_index:current_index + 1]
        
        if len(window_data) < 2:
            return None
        
        # Simple linear regression: slope = (n*Σ(xy) - Σ(x)*Σ(y)) / (n*Σ(x²) - (Σ(x))²)
        n = len(window_data)
        x_values = list(range(n))  # Day indices (0, 1, 2, ...)
        y_values = [s['value'] for s in window_data]
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x * x for x in x_values)
        
        denominator = n * sum_x_squared - sum_x * sum_x
        
        if denominator == 0:
            return 0.0  # Flat trend
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        return round(slope, 4)
    
    def update_all_metrics_analytics(self, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Update moving averages and trends for all automated metrics.
        
        Args:
            end_date: End date for computation (default: today)
            
        Returns:
            Dictionary with results for each metric
        """
        if not end_date:
            end_date = date.today().isoformat()
        
        results = {}
        
        for metric in MetricType.all():
            logger.info(f"Updating analytics for {metric}")
            results[metric] = self.compute_moving_averages_and_trends(metric, end_date)
        
        return {
            'end_date': end_date,
            'metrics_processed': len(results),
            'results': results
        }
    
    def get_summary_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for the last N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            end_date = date.today().isoformat()
            start_date = (date.today() - timedelta(days=days)).isoformat()
            
            stats = {
                'date_range': (start_date, end_date),
                'days_analyzed': days,
                'metrics': {}
            }
            
            for metric in MetricType.all():
                summaries = self.db.get_daily_summaries_for_metric(metric, start_date, end_date)
                
                if summaries:
                    values = [s['value'] for s in summaries]
                    
                    metric_stats = {
                        'data_points': len(summaries),
                        'latest_value': values[-1] if values else None,
                        'average': round(sum(values) / len(values), 2) if values else None,
                        'min_value': min(values) if values else None,
                        'max_value': max(values) if values else None,
                        'latest_summary': summaries[-1] if summaries else None
                    }
                    
                    stats['metrics'][metric] = metric_stats
                else:
                    stats['metrics'][metric] = {
                        'data_points': 0,
                        'latest_value': None,
                        'average': None,
                        'min_value': None,
                        'max_value': None,
                        'latest_summary': None
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting summary statistics: {e}")
            return {
                'error': str(e),
                'metrics': {}
            }


def compute_daily_summaries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_recompute: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to compute daily summaries.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        force_recompute: If True, recompute existing summaries
        
    Returns:
        Dictionary with computation results
    """
    computer = SummaryComputer()
    return computer.compute_daily_summaries(start_date, end_date, force_recompute)


def update_all_analytics(end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to update all metrics analytics.
    
    Args:
        end_date: End date for computation
        
    Returns:
        Dictionary with results for each metric
    """
    computer = SummaryComputer()
    return computer.update_all_metrics_analytics(end_date)