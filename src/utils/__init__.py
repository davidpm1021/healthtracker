"""
Utility functions for Health Tracker
"""
from .date_helpers import (
    get_date_range,
    get_week_boundaries,
    get_month_boundaries,
    get_consecutive_date_ranges,
    find_longest_streak,
    find_current_streak,
    get_missing_dates_in_range,
    get_streak_risk_dates,
    calculate_achievement_frequency,
    get_weekly_achievement_summary,
    format_streak_duration,
    get_next_milestone_days,
    is_weekend,
    get_business_days_in_range,
    days_until_date
)

__all__ = [
    "get_date_range",
    "get_week_boundaries", 
    "get_month_boundaries",
    "get_consecutive_date_ranges",
    "find_longest_streak",
    "find_current_streak",
    "get_missing_dates_in_range",
    "get_streak_risk_dates",
    "calculate_achievement_frequency",
    "get_weekly_achievement_summary",
    "format_streak_duration",
    "get_next_milestone_days",
    "is_weekend",
    "get_business_days_in_range",
    "days_until_date"
]