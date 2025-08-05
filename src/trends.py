"""
Trend analysis and moving average calculations for Health Tracker.
Provides utility functions for analyzing metric trends and patterns.
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import math


# Set up logging
logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends and patterns in health metric data."""
    
    @staticmethod
    def compute_moving_average(values: List[float], window_size: int) -> List[Optional[float]]:
        """
        Compute moving average for a series of values.
        
        Args:
            values: List of numeric values
            window_size: Size of the moving window
            
        Returns:
            List of moving averages (None for positions where window is incomplete)
        """
        if not values or window_size <= 0:
            return [None] * len(values)
        
        moving_averages = []
        
        for i in range(len(values)):
            if i < window_size - 1:
                # Not enough data points for full window
                moving_averages.append(None)
            else:
                # Compute average for the window
                window_values = values[i - window_size + 1:i + 1]
                avg = sum(window_values) / len(window_values)
                moving_averages.append(round(avg, 2))
        
        return moving_averages
    
    @staticmethod
    def compute_exponential_moving_average(values: List[float], alpha: float = 0.3) -> List[Optional[float]]:
        """
        Compute exponential moving average (EMA) for a series of values.
        
        Args:
            values: List of numeric values
            alpha: Smoothing factor (0 < alpha <= 1, higher = more responsive)
            
        Returns:
            List of exponential moving averages
        """
        if not values or alpha <= 0 or alpha > 1:
            return [None] * len(values)
        
        ema_values = []
        
        for i, value in enumerate(values):
            if i == 0:
                # First value is the starting point
                ema_values.append(value)
            else:
                # EMA = alpha * current_value + (1 - alpha) * previous_ema
                ema = alpha * value + (1 - alpha) * ema_values[i - 1]
                ema_values.append(round(ema, 2))
        
        return ema_values
    
    @staticmethod
    def compute_linear_trend(values: List[float], days: Optional[List[int]] = None) -> Dict[str, float]:
        """
        Compute linear trend using least squares regression.
        
        Args:
            values: List of numeric values
            days: List of day indices (default: 0, 1, 2, ...)
            
        Returns:
            Dictionary with slope, intercept, and correlation coefficient
        """
        if len(values) < 2:
            return {'slope': 0.0, 'intercept': 0.0, 'correlation': 0.0}
        
        if days is None:
            days = list(range(len(values)))
        
        if len(days) != len(values):
            raise ValueError("Days and values lists must have the same length")
        
        n = len(values)
        
        # Calculate means
        mean_x = sum(days) / n
        mean_y = sum(values) / n
        
        # Calculate slope and intercept
        numerator = sum((days[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((days[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0.0
            intercept = mean_y
        else:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
        
        # Calculate correlation coefficient
        if denominator == 0:
            correlation = 0.0
        else:
            sum_y_dev_sq = sum((values[i] - mean_y) ** 2 for i in range(n))
            if sum_y_dev_sq == 0:
                correlation = 0.0
            else:
                correlation = numerator / math.sqrt(denominator * sum_y_dev_sq)
        
        return {
            'slope': round(slope, 4),
            'intercept': round(intercept, 2),
            'correlation': round(correlation, 3)
        }
    
    @staticmethod
    def classify_trend(slope: float, threshold: float = 0.01) -> str:
        """
        Classify trend as increasing, decreasing, or flat.
        
        Args:
            slope: Trend slope value
            threshold: Minimum slope magnitude to classify as trending
            
        Returns:
            Trend classification: 'increasing', 'decreasing', or 'flat'
        """
        if abs(slope) < threshold:
            return 'flat'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    @staticmethod
    def detect_outliers(values: List[float], method: str = 'iqr', factor: float = 1.5) -> List[bool]:
        """
        Detect outliers in a series of values.
        
        Args:
            values: List of numeric values
            method: Outlier detection method ('iqr' or 'zscore')
            factor: Outlier factor (1.5 for IQR, 2-3 for z-score)
            
        Returns:
            List of booleans indicating outliers
        """
        if len(values) < 4:  # Need at least 4 points for meaningful outlier detection
            return [False] * len(values)
        
        if method == 'iqr':
            return TrendAnalyzer._detect_outliers_iqr(values, factor)
        elif method == 'zscore':
            return TrendAnalyzer._detect_outliers_zscore(values, factor)
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
    
    @staticmethod
    def _detect_outliers_iqr(values: List[float], factor: float) -> List[bool]:
        """Detect outliers using Interquartile Range (IQR) method."""
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        # Calculate Q1 and Q3
        q1_index = n // 4
        q3_index = 3 * n // 4
        
        q1 = sorted_values[q1_index]
        q3 = sorted_values[q3_index]
        
        iqr = q3 - q1
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        
        return [value < lower_bound or value > upper_bound for value in values]
    
    @staticmethod
    def _detect_outliers_zscore(values: List[float], factor: float) -> List[bool]:
        """Detect outliers using Z-score method."""
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return [False] * len(values)
        
        z_scores = [(value - mean_val) / std_dev for value in values]
        return [abs(z_score) > factor for z_score in z_scores]
    
    @staticmethod
    def calculate_volatility(values: List[float]) -> float:
        """
        Calculate volatility (standard deviation) of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Standard deviation of the values
        """
        if len(values) < 2:
            return 0.0
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
        return round(math.sqrt(variance), 3)
    
    @staticmethod
    def find_peaks_and_valleys(values: List[float], min_prominence: float = 0.1) -> Dict[str, List[int]]:
        """
        Find peaks and valleys in a series of values.
        
        Args:
            values: List of numeric values
            min_prominence: Minimum prominence for a peak/valley
            
        Returns:
            Dictionary with 'peaks' and 'valleys' indices
        """
        if len(values) < 3:
            return {'peaks': [], 'valleys': []}
        
        peaks = []
        valleys = []
        
        for i in range(1, len(values) - 1):
            # Check for peak (local maximum)
            if values[i] > values[i-1] and values[i] > values[i+1]:
                prominence = min(values[i] - values[i-1], values[i] - values[i+1])
                if prominence >= min_prominence:
                    peaks.append(i)
            
            # Check for valley (local minimum)
            elif values[i] < values[i-1] and values[i] < values[i+1]:
                prominence = min(values[i-1] - values[i], values[i+1] - values[i])
                if prominence >= min_prominence:
                    valleys.append(i)
        
        return {'peaks': peaks, 'valleys': valleys}


def analyze_metric_trends(
    summaries: List[Dict[str, Any]], 
    metric: str,
    analysis_window: int = 30
) -> Dict[str, Any]:
    """
    Comprehensive trend analysis for a metric.
    
    Args:
        summaries: List of daily summary dictionaries
        metric: Metric name for labeling
        analysis_window: Number of days to analyze for trends
        
    Returns:
        Dictionary with comprehensive trend analysis
    """
    if not summaries:
        return {
            'metric': metric,
            'error': 'No data provided',
            'data_points': 0
        }
    
    # Sort by date and extract values
    summaries.sort(key=lambda x: x['date'])
    values = [s['value'] for s in summaries]
    dates = [s['date'] for s in summaries]
    
    analyzer = TrendAnalyzer()
    
    # Limit analysis to the specified window
    if len(values) > analysis_window:
        values = values[-analysis_window:]
        dates = dates[-analysis_window:]
    
    # Compute various analyses
    trend = analyzer.compute_linear_trend(values)
    trend_classification = analyzer.classify_trend(trend['slope'])
    
    moving_avg_7 = analyzer.compute_moving_average(values, 7)
    moving_avg_30 = analyzer.compute_moving_average(values, 30)
    
    volatility = analyzer.calculate_volatility(values)
    outliers = analyzer.detect_outliers(values)
    peaks_valleys = analyzer.find_peaks_and_valleys(values)
    
    # Calculate recent performance
    recent_values = values[-7:] if len(values) >= 7 else values
    recent_avg = sum(recent_values) / len(recent_values) if recent_values else 0
    
    overall_avg = sum(values) / len(values) if values else 0
    recent_vs_overall = ((recent_avg - overall_avg) / overall_avg * 100) if overall_avg != 0 else 0
    
    return {
        'metric': metric,
        'data_points': len(values),
        'date_range': (dates[0], dates[-1]) if dates else None,
        'current_value': values[-1] if values else None,
        'trend': {
            'slope': trend['slope'],
            'intercept': trend['intercept'],
            'correlation': trend['correlation'],
            'classification': trend_classification
        },
        'moving_averages': {
            '7_day_latest': moving_avg_7[-1] if moving_avg_7 and moving_avg_7[-1] is not None else None,
            '30_day_latest': moving_avg_30[-1] if moving_avg_30 and moving_avg_30[-1] is not None else None
        },
        'statistics': {
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'average': round(overall_avg, 2) if values else None,
            'recent_average_7d': round(recent_avg, 2) if recent_values else None,
            'recent_vs_overall_pct': round(recent_vs_overall, 1),
            'volatility': volatility
        },
        'patterns': {
            'outlier_count': sum(outliers),
            'outlier_indices': [i for i, is_outlier in enumerate(outliers) if is_outlier],
            'peaks': peaks_valleys['peaks'],
            'valleys': peaks_valleys['valleys']
        }
    }