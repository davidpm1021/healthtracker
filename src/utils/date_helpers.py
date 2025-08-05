"""
Date Utility Functions - Health Tracker
Helper functions for date calculations, range generation, and streak processing
"""
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional, Dict, Any
from calendar import monthrange
import logging

logger = logging.getLogger(__name__)


def get_date_range(start_date: date, end_date: date, include_end: bool = True) -> List[date]:
    """
    Generate a list of dates between start and end dates.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date
        include_end: Whether to include end_date in result
    
    Returns:
        List of dates in the range
    """
    dates = []
    current = start_date
    
    while current < end_date or (include_end and current <= end_date):
        dates.append(current)
        current += timedelta(days=1)
        
        # Safety check to prevent infinite loops
        if len(dates) > 10000:
            logger.warning("Date range exceeded 10000 days, truncating")
            break
    
    return dates


def get_week_boundaries(target_date: date) -> Tuple[date, date]:
    """
    Get start (Monday) and end (Sunday) dates for the week containing target_date.
    
    Args:
        target_date: Date to find week boundaries for
    
    Returns:
        Tuple of (week_start, week_end)
    """
    # Get Monday of the week (weekday() returns 0 for Monday)
    days_since_monday = target_date.weekday()
    week_start = target_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def get_month_boundaries(target_date: date) -> Tuple[date, date]:
    """
    Get first and last dates of the month containing target_date.
    
    Args:
        target_date: Date to find month boundaries for
    
    Returns:
        Tuple of (month_start, month_end)
    """
    month_start = target_date.replace(day=1)
    last_day_of_month = monthrange(target_date.year, target_date.month)[1]
    month_end = target_date.replace(day=last_day_of_month)
    
    return month_start, month_end


def get_consecutive_date_ranges(dates: List[date]) -> List[List[date]]:
    """
    Group consecutive dates into ranges.
    
    Args:
        dates: List of dates (will be sorted)
    
    Returns:
        List of lists, each containing consecutive dates
    """
    if not dates:
        return []
    
    # Sort dates to ensure proper grouping
    sorted_dates = sorted(set(dates))
    
    ranges = []
    current_range = [sorted_dates[0]]
    
    for i in range(1, len(sorted_dates)):
        current_date = sorted_dates[i]
        previous_date = sorted_dates[i - 1]
        
        # Check if dates are consecutive (1 day apart)
        if (current_date - previous_date).days == 1:
            current_range.append(current_date)
        else:
            # Gap found, start new range
            ranges.append(current_range)
            current_range = [current_date]
    
    # Add the last range
    ranges.append(current_range)
    
    return ranges


def find_longest_streak(dates: List[date], end_date: Optional[date] = None) -> Tuple[int, Optional[date], Optional[date]]:
    """
    Find the longest consecutive streak of dates.
    
    Args:
        dates: List of dates to analyze
        end_date: Optional end date to consider (defaults to today)
    
    Returns:
        Tuple of (streak_length, streak_start_date, streak_end_date)
    """
    if not dates:
        return 0, None, None
    
    if not end_date:
        end_date = date.today()
    
    # Filter dates up to end_date
    valid_dates = [d for d in dates if d <= end_date]
    
    if not valid_dates:
        return 0, None, None
    
    # Get all consecutive ranges
    ranges = get_consecutive_date_ranges(valid_dates)
    
    # Find the longest range
    longest_range = max(ranges, key=len)
    
    return len(longest_range), longest_range[0], longest_range[-1]


def find_current_streak(dates: List[date], as_of_date: Optional[date] = None) -> Tuple[int, Optional[date]]:
    """
    Find the current active streak ending on or before as_of_date.
    
    Args:
        dates: List of achievement dates
        as_of_date: Date to check streak as of (defaults to today)
    
    Returns:
        Tuple of (current_streak_length, streak_start_date)
    """
    if not as_of_date:
        as_of_date = date.today()
    
    if not dates:
        return 0, None
    
    # Filter and sort dates up to as_of_date
    valid_dates = sorted([d for d in dates if d <= as_of_date])
    
    if not valid_dates:
        return 0, None
    
    # Work backwards from as_of_date to find current streak
    current_streak_length = 0
    check_date = as_of_date
    
    while check_date in valid_dates:
        current_streak_length += 1
        check_date -= timedelta(days=1)
        
        # Safety check to prevent very long lookbacks
        if current_streak_length > 1000:
            logger.warning("Current streak calculation exceeded 1000 days")
            break
    
    if current_streak_length == 0:
        return 0, None
    
    # Streak start date is check_date + 1 (since check_date is the first non-streak date)
    streak_start = check_date + timedelta(days=1)
    
    return current_streak_length, streak_start


def get_missing_dates_in_range(start_date: date, end_date: date, 
                              existing_dates: List[date]) -> List[date]:
    """
    Find dates missing from a range compared to existing dates.
    
    Args:
        start_date: Start of range to check
        end_date: End of range to check
        existing_dates: Dates that already exist
    
    Returns:
        List of missing dates in the range
    """
    expected_dates = set(get_date_range(start_date, end_date))
    existing_dates_set = set(existing_dates)
    
    missing_dates = expected_dates - existing_dates_set
    
    return sorted(list(missing_dates))


def get_streak_risk_dates(achievement_dates: List[date], 
                         as_of_date: Optional[date] = None) -> List[date]:
    """
    Identify dates where streaks were at risk (gaps of 1 day).
    
    Args:
        achievement_dates: List of dates with achievements
        as_of_date: Date to analyze up to (defaults to today)
    
    Returns:
        List of dates where streak was at risk
    """
    if not as_of_date:
        as_of_date = date.today()
    
    if not achievement_dates:
        return []
    
    # Sort valid dates
    valid_dates = sorted([d for d in achievement_dates if d <= as_of_date])
    
    risk_dates = []
    
    for i in range(len(valid_dates) - 1):
        current_date = valid_dates[i]
        next_date = valid_dates[i + 1]
        
        gap_days = (next_date - current_date).days
        
        if gap_days == 2:  # 1 day gap means streak was at risk
            risk_date = current_date + timedelta(days=1)
            risk_dates.append(risk_date)
    
    return risk_dates


def calculate_achievement_frequency(achievement_dates: List[date], 
                                  window_days: int = 30) -> Dict[str, float]:
    """
    Calculate achievement frequency statistics.
    
    Args:
        achievement_dates: List of achievement dates
        window_days: Number of days to analyze (from most recent)
    
    Returns:
        Dictionary with frequency statistics
    """
    if not achievement_dates:
        return {
            "total_achievements": 0,
            "achievements_per_day": 0.0,
            "achievements_per_week": 0.0,
            "consistency_percentage": 0.0
        }
    
    # Get recent achievements within window
    end_date = date.today()
    start_date = end_date - timedelta(days=window_days - 1)
    
    recent_achievements = [d for d in achievement_dates if start_date <= d <= end_date]
    
    total_days = window_days
    achievement_days = len(set(recent_achievements))  # Unique days
    
    return {
        "total_achievements": len(recent_achievements),
        "achievement_days": achievement_days,
        "achievements_per_day": len(recent_achievements) / total_days,
        "achievements_per_week": (len(recent_achievements) / total_days) * 7,
        "consistency_percentage": (achievement_days / total_days) * 100,
        "window_days": window_days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }


def get_weekly_achievement_summary(achievement_dates: List[date], 
                                 weeks_back: int = 12) -> List[Dict[str, Any]]:
    """
    Get weekly summary of achievements for the past N weeks.
    
    Args:
        achievement_dates: List of achievement dates
        weeks_back: Number of weeks to include
    
    Returns:
        List of weekly summaries
    """
    if not achievement_dates:
        return []
    
    # Get date range for analysis
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks_back)
    
    # Filter achievements to the window
    valid_achievements = [d for d in achievement_dates if start_date <= d <= end_date]
    
    weekly_summaries = []
    
    # Generate weekly summaries
    current_date = end_date
    for week_num in range(weeks_back):
        week_start, week_end = get_week_boundaries(current_date)
        
        # Count achievements in this week
        week_achievements = [d for d in valid_achievements if week_start <= d <= week_end]
        
        weekly_summaries.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "achievement_count": len(week_achievements),
            "achievement_days": len(set(week_achievements)),
            "week_number": week_num + 1,
            "is_current_week": week_num == 0
        })
        
        # Move to previous week
        current_date = week_start - timedelta(days=1)
    
    return weekly_summaries


def format_streak_duration(days: int) -> str:
    """
    Format streak duration in a human-readable way.
    
    Args:
        days: Number of days in streak
    
    Returns:
        Formatted string
    """
    if days == 0:
        return "No streak"
    elif days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        remaining_days = days % 7
        if remaining_days == 0:
            return f"{weeks} {'week' if weeks == 1 else 'weeks'}"
        else:
            return f"{weeks}w {remaining_days}d"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if remaining_days == 0:
            return f"{months} {'month' if months == 1 else 'months'}"
        else:
            return f"{months}m {remaining_days}d"
    else:
        years = days // 365
        remaining_days = days % 365
        if remaining_days == 0:
            return f"{years} {'year' if years == 1 else 'years'}"
        else:
            return f"{years}y {remaining_days}d"


def get_next_milestone_days(current_streak: int) -> int:
    """
    Get the number of days until the next streak milestone.
    
    Args:
        current_streak: Current streak length in days
    
    Returns:
        Days until next milestone
    """
    milestones = [7, 14, 30, 50, 100, 200, 365, 500, 1000]
    
    for milestone in milestones:
        if current_streak < milestone:
            return milestone - current_streak
    
    # For very long streaks, next milestone is next 100 days
    return 100 - (current_streak % 100)


def is_weekend(target_date: date) -> bool:
    """Check if date falls on weekend (Saturday or Sunday)."""
    return target_date.weekday() >= 5


def get_business_days_in_range(start_date: date, end_date: date) -> List[date]:
    """Get all business days (Monday-Friday) in date range."""
    all_dates = get_date_range(start_date, end_date)
    return [d for d in all_dates if not is_weekend(d)]


def days_until_date(target_date: date, from_date: Optional[date] = None) -> int:
    """
    Calculate days until target date.
    
    Args:
        target_date: Target date
        from_date: Starting date (defaults to today)
    
    Returns:
        Number of days (negative if target is in past)
    """
    if not from_date:
        from_date = date.today()
    
    return (target_date - from_date).days