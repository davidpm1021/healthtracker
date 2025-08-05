"""
Chart data endpoints for Health Tracker dashboard.
Provides formatted data for Chart.js visualizations.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import logging

from ..database import DatabaseManager
from ..models import MetricType, ManualMetricType
from ..trends import TrendAnalyzer

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/charts/{metric}")
async def get_chart_data(
    metric: str,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get chart data for a specific metric and time period.
    
    Args:
        metric: Metric type (steps, sleep, weight, heart_rate, hrv)
        period: Time period (week, month)
        start_date: Optional custom start date
        end_date: Optional custom end date
        
    Returns:
        Chart data formatted for Chart.js
    """
    try:
        db = DatabaseManager()
        
        # Determine date range
        if start_date and end_date:
            date_range = (start_date, end_date)
        else:
            date_range = _calculate_date_range(period)
        
        # Validate metric type
        if metric not in [MetricType.STEPS, MetricType.SLEEP, MetricType.WEIGHT, 
                         MetricType.HEART_RATE, ManualMetricType.HRV]:
            raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
        
        # Get chart data based on metric type
        if metric == ManualMetricType.HRV:
            chart_data = await _get_manual_chart_data(db, metric, date_range)
        else:
            chart_data = await _get_automated_chart_data(db, metric, date_range)
        
        return chart_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chart data for {metric}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate chart data")


@router.get("/charts/summary/week")
async def get_week_summary():
    """
    Get weekly summary statistics for the week view header.
    
    Returns:
        Summary statistics for current week
    """
    try:
        db = DatabaseManager()
        date_range = _calculate_date_range("week")
        
        summary = {
            "totalSteps": 0,
            "avgSleep": 0,
            "activeDays": 0,
            "weekRange": f"{date_range[0]} to {date_range[1]}"
        }
        
        # Calculate total steps
        steps_data = db.get_daily_summaries_for_metric(MetricType.STEPS, date_range[0], date_range[1])
        if steps_data:
            summary["totalSteps"] = sum(d.get('value', 0) for d in steps_data if d.get('value'))
            summary["activeDays"] = len([d for d in steps_data if d.get('value', 0) > 1000])
        
        # Calculate average sleep
        sleep_data = db.get_daily_summaries_for_metric(MetricType.SLEEP, date_range[0], date_range[1])
        if sleep_data:
            valid_sleep = [d.get('value', 0) for d in sleep_data if d.get('value')]
            if valid_sleep:
                avg_minutes = sum(valid_sleep) / len(valid_sleep)
                summary["avgSleep"] = round(avg_minutes / 60, 1)  # Convert to hours
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating week summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate week summary")


@router.get("/charts/insights/week")
async def get_week_insights():
    """
    Get insights and recommendations for the current week.
    
    Returns:
        List of insights based on weekly data patterns
    """
    try:
        db = DatabaseManager()
        date_range = _calculate_date_range("week")
        prev_week_range = _calculate_date_range("week", weeks_offset=-1)
        
        insights = []
        
        # Steps insights
        steps_insights = await _generate_steps_insights(db, date_range, prev_week_range)
        insights.extend(steps_insights)
        
        # Sleep insights
        sleep_insights = await _generate_sleep_insights(db, date_range, prev_week_range)
        insights.extend(sleep_insights)
        
        # Heart rate insights
        hr_insights = await _generate_heart_rate_insights(db, date_range)
        insights.extend(hr_insights)
        
        # Manual entry insights
        manual_insights = await _generate_manual_entry_insights(db, date_range)
        insights.extend(manual_insights)
        
        # Limit to top 5 insights
        return insights[:5]
        
    except Exception as e:
        logger.error(f"Error generating week insights: {e}")
        return ["Unable to generate insights at this time."]


async def _get_automated_chart_data(db: DatabaseManager, metric: str, date_range: tuple) -> Dict[str, Any]:
    """Get chart data for automated metrics (steps, sleep, weight, heart_rate)."""
    
    # Get daily summaries
    summaries = db.get_daily_summaries_for_metric(metric, date_range[0], date_range[1])
    
    if not summaries:
        return _empty_chart_data(date_range)
    
    # Generate date labels
    labels = _generate_date_labels(date_range)
    
    # Extract values and align with date labels
    values = []
    summary_dict = {s['date']: s for s in summaries}
    
    current_date = datetime.fromisoformat(date_range[0]).date()
    end_date = datetime.fromisoformat(date_range[1]).date()
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        if date_str in summary_dict:
            value = summary_dict[date_str].get('value', 0)
            # Convert sleep minutes to hours for display
            if metric == MetricType.SLEEP and value:
                values.append(value)  # Keep as minutes for Chart.js to convert
            else:
                values.append(value or 0)
        else:
            values.append(0)
        current_date += timedelta(days=1)
    
    # Calculate moving averages for weight and heart rate
    moving_average = None
    if metric in [MetricType.WEIGHT, MetricType.HEART_RATE]:
        moving_average = _calculate_moving_average(values, window=3)
    
    # Determine trend
    trend = _calculate_trend(values)
    
    return {
        "labels": labels,
        "values": values,
        "movingAverage": moving_average,
        "trend": trend,
        "period": _format_period_label(date_range),
        "metric": metric,
        "unit": _get_metric_unit(metric)
    }


async def _get_manual_chart_data(db: DatabaseManager, metric: str, date_range: tuple) -> Dict[str, Any]:
    """Get chart data for manual entry metrics (HRV)."""
    
    # Get manual entries
    entries = db.get_manual_entries(metric, date_range[0], date_range[1])
    
    if not entries:
        return _empty_chart_data(date_range)
    
    # Extract dates and values
    labels = []
    values = []
    
    for entry in entries:
        entry_date = datetime.fromisoformat(entry['date']).strftime('%a')
        labels.append(entry_date)
        values.append(entry.get('value', 0))
    
    return {
        "labels": labels,
        "values": values,
        "trend": "manual",  # No automated trend for manual entries
        "period": _format_period_label(date_range),
        "metric": metric,
        "unit": _get_metric_unit(metric),
        "entryCount": len(entries)
    }


def _calculate_date_range(period: str, weeks_offset: int = 0) -> tuple:
    """Calculate start and end dates for a given period."""
    today = date.today()
    
    if period == "week":
        # Get Monday of current week (or offset week)
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday) + timedelta(weeks=weeks_offset)
        sunday = monday + timedelta(days=6)
        return (monday.isoformat(), sunday.isoformat())
    
    elif period == "month":
        # Get first and last day of current month (or offset month)
        if weeks_offset != 0:
            # Approximate month offset using weeks
            target_date = today + timedelta(weeks=weeks_offset * 4)
        else:
            target_date = today
            
        first_day = target_date.replace(day=1)
        
        # Get last day of month
        if target_date.month == 12:
            last_day = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
        
        return (first_day.isoformat(), last_day.isoformat())
    
    else:
        # Default to week
        return _calculate_date_range("week", weeks_offset)


def _generate_date_labels(date_range: tuple) -> List[str]:
    """Generate formatted date labels for chart x-axis."""
    start_date = datetime.fromisoformat(date_range[0]).date()
    end_date = datetime.fromisoformat(date_range[1]).date()
    
    labels = []
    current_date = start_date
    
    # Determine label format based on date range
    days_diff = (end_date - start_date).days
    
    if days_diff <= 7:
        # Week view: use day names
        while current_date <= end_date:
            labels.append(current_date.strftime('%a'))
            current_date += timedelta(days=1)
    else:
        # Month view: use MM/DD format
        while current_date <= end_date:
            labels.append(current_date.strftime('%m/%d'))
            current_date += timedelta(days=1)
    
    return labels


def _calculate_moving_average(values: List[float], window: int = 7) -> List[float]:
    """Calculate moving average for chart data."""
    if len(values) < window:
        return values
    
    moving_avg = []
    for i in range(len(values)):
        if i < window - 1:
            # For early values, use available data
            avg = sum(values[:i+1]) / (i + 1)
        else:
            # Use full window
            avg = sum(values[i-window+1:i+1]) / window
        moving_avg.append(round(avg, 2))
    
    return moving_avg


def _calculate_trend(values: List[float]) -> str:
    """Calculate trend direction from values."""
    if len(values) < 2:
        return "stable"
    
    # Simple trend calculation - compare first half to second half
    mid = len(values) // 2
    if mid == 0:
        return "stable"
    
    first_half_avg = sum(values[:mid]) / mid
    second_half_avg = sum(values[mid:]) / (len(values) - mid)
    
    diff_pct = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
    
    if abs(diff_pct) < 0.05:  # Less than 5% change
        return "stable"
    elif diff_pct > 0:
        return "up"
    else:
        return "down"


def _empty_chart_data(date_range: tuple) -> Dict[str, Any]:
    """Return empty chart data structure."""
    return {
        "labels": _generate_date_labels(date_range),
        "values": [],
        "trend": "stable",
        "period": _format_period_label(date_range),
        "message": "No data available for this period"
    }


def _format_period_label(date_range: tuple) -> str:
    """Format period label for display."""
    start_date = datetime.fromisoformat(date_range[0]).date()
    end_date = datetime.fromisoformat(date_range[1]).date()
    
    if (end_date - start_date).days <= 7:
        return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
    else:
        return f"{start_date.strftime('%b %Y')}"


def _get_metric_unit(metric: str) -> str:
    """Get display unit for metric."""
    units = {
        MetricType.STEPS: "steps",
        MetricType.SLEEP: "hours",
        MetricType.WEIGHT: "kg",
        MetricType.HEART_RATE: "bpm",
        ManualMetricType.HRV: "ms"
    }
    return units.get(metric, "")


async def _generate_steps_insights(db: DatabaseManager, current_week: tuple, prev_week: tuple) -> List[str]:
    """Generate steps-related insights."""
    insights = []
    
    try:
        current_data = db.get_daily_summaries_for_metric(MetricType.STEPS, current_week[0], current_week[1])
        prev_data = db.get_daily_summaries_for_metric(MetricType.STEPS, prev_week[0], prev_week[1])
        
        if current_data:
            current_total = sum(d.get('value', 0) for d in current_data if d.get('value'))
            goal_days = len([d for d in current_data if d.get('value', 0) >= 10000])
            
            if prev_data:
                prev_total = sum(d.get('value', 0) for d in prev_data if d.get('value'))
                if prev_total > 0:
                    change_pct = ((current_total - prev_total) / prev_total) * 100
                    if abs(change_pct) > 5:
                        direction = "increased" if change_pct > 0 else "decreased"
                        insights.append(f"📈 Your step count {direction} by {abs(change_pct):.0f}% compared to last week")
            
            if goal_days > 0:
                insights.append(f"🎯 You reached your 10k step goal on {goal_days} day{'s' if goal_days != 1 else ''} this week")
        
    except Exception as e:
        logger.error(f"Error generating steps insights: {e}")
    
    return insights


async def _generate_sleep_insights(db: DatabaseManager, current_week: tuple, prev_week: tuple) -> List[str]:
    """Generate sleep-related insights."""
    insights = []
    
    try:
        current_data = db.get_daily_summaries_for_metric(MetricType.SLEEP, current_week[0], current_week[1])
        
        if current_data:
            valid_sleep = [d.get('value', 0) for d in current_data if d.get('value')]
            if valid_sleep:
                avg_hours = sum(valid_sleep) / len(valid_sleep) / 60
                target_nights = len([h for h in valid_sleep if h >= 7 * 60])  # 7+ hours
                
                if avg_hours >= 8:
                    insights.append(f"😴 Excellent sleep this week - averaging {avg_hours:.1f} hours per night")
                elif avg_hours >= 7:
                    insights.append(f"💤 Good sleep consistency - {target_nights}/{len(valid_sleep)} nights in target range")
                else:
                    insights.append(f"⏰ Consider aiming for 7-8 hours - currently averaging {avg_hours:.1f}h")
        
    except Exception as e:
        logger.error(f"Error generating sleep insights: {e}")
    
    return insights


async def _generate_heart_rate_insights(db: DatabaseManager, date_range: tuple) -> List[str]:
    """Generate heart rate insights."""
    insights = []
    
    try:
        hr_data = db.get_daily_summaries_for_metric(MetricType.HEART_RATE, date_range[0], date_range[1])
        
        if hr_data:
            valid_hr = [d.get('value', 0) for d in hr_data if d.get('value')]
            if valid_hr:
                avg_hr = sum(valid_hr) / len(valid_hr)
                if 60 <= avg_hr <= 80:
                    insights.append("❤️ Heart rate shows healthy patterns this week")
                elif avg_hr < 60:
                    insights.append("💪 Low resting heart rate indicates good fitness")
        
    except Exception as e:
        logger.error(f"Error generating heart rate insights: {e}")
    
    return insights


async def _generate_manual_entry_insights(db: DatabaseManager, date_range: tuple) -> List[str]:
    """Generate insights for manual entries."""
    insights = []
    
    try:
        # Check HRV consistency
        hrv_entries = db.get_manual_entries(ManualMetricType.HRV, date_range[0], date_range[1])
        if len(hrv_entries) >= 3:
            insights.append(f"💓 Great job logging HRV {len(hrv_entries)} times this week")
        
        # Check mood patterns
        mood_entries = db.get_manual_entries(ManualMetricType.MOOD, date_range[0], date_range[1])
        if mood_entries:
            avg_mood = sum(e.get('value', 0) for e in mood_entries) / len(mood_entries)
            if avg_mood >= 7:
                insights.append("😊 Your mood ratings show a positive week")
        
    except Exception as e:
        logger.error(f"Error generating manual entry insights: {e}")
    
    return insights