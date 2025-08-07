"""
Goal Progress Tracking Service - Health Tracker
Real-time progress calculation and achievement detection for health goals
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ..database import DatabaseManager
from ..models.goals import Goal, GoalAchievement, GoalType, GoalFrequency
from ..models import RawPoint, DailySummary, ManualEntry
from .streak_engine import StreakEngine
from ..utils.date_helpers import get_date_range, get_week_boundaries, get_month_boundaries

logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    """Progress snapshot for a goal at a specific point in time"""
    goal_id: int
    date: date
    target_value: float
    actual_value: float
    progress_percentage: float
    is_achieved: bool
    data_source: str
    raw_data_points: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'goal_id': self.goal_id,
            'date': self.date.isoformat(),
            'target_value': self.target_value,
            'actual_value': self.actual_value,
            'progress_percentage': self.progress_percentage,
            'is_achieved': self.is_achieved,
            'data_source': self.data_source,
            'raw_data_points': self.raw_data_points
        }


class ProgressTracker:
    """Service for tracking goal progress and detecting achievements"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.streak_engine = StreakEngine()
    
    def calculate_current_progress(self, goal: Goal, as_of_date: Optional[date] = None) -> ProgressSnapshot:
        """
        Calculate current progress for a goal.
        
        Args:
            goal: Goal to calculate progress for
            as_of_date: Date to calculate progress as of (defaults to today)
        
        Returns:
            ProgressSnapshot with current progress
        """
        if not as_of_date:
            as_of_date = date.today()
        
        try:
            if goal.frequency == GoalFrequency.DAILY.value:
                return self._calculate_daily_progress(goal, as_of_date)
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                return self._calculate_weekly_progress(goal, as_of_date)
            else:
                logger.warning(f"Unknown frequency for goal {goal.id}: {goal.frequency}")
                return ProgressSnapshot(
                    goal_id=goal.id,
                    date=as_of_date,
                    target_value=goal.target_value,
                    actual_value=0.0,
                    progress_percentage=0.0,
                    is_achieved=False,
                    data_source="unknown"
                )
                
        except Exception as e:
            logger.error(f"Error calculating progress for goal {goal.id}: {e}")
            raise
    
    def _calculate_daily_progress(self, goal: Goal, target_date: date) -> ProgressSnapshot:
        """Calculate progress for daily goals"""
        
        # Get health data for the target date
        actual_value = 0.0
        data_source = "none"
        raw_data_points = 0
        
        if goal.goal_type == GoalType.STEPS.value:
            actual_value, raw_data_points = self._get_steps_for_date(target_date)
            data_source = "steps_data"
            
        elif goal.goal_type == GoalType.SLEEP_DURATION.value:
            actual_value, raw_data_points = self._get_sleep_duration_for_date(target_date)
            data_source = "sleep_data"
            
        elif goal.goal_type == GoalType.WEIGHT_LOGGING.value:
            actual_value, raw_data_points = self._get_weight_entries_for_date(target_date)
            data_source = "weight_data"
            
        elif goal.goal_type == GoalType.HRV_ENTRY.value:
            actual_value, raw_data_points = self._get_hrv_entries_for_date(target_date)
            data_source = "manual_entries"
            
        elif goal.goal_type == GoalType.HEART_RATE_ZONE.value:
            actual_value, raw_data_points = self._get_heart_rate_zone_minutes_for_date(target_date)
            data_source = "heart_rate_data"
        
        # Calculate progress percentage
        progress_percentage = min((actual_value / goal.target_value) * 100, 100.0) if goal.target_value > 0 else 0.0
        is_achieved = actual_value >= goal.target_value
        
        return ProgressSnapshot(
            goal_id=goal.id,
            date=target_date,
            target_value=goal.target_value,
            actual_value=actual_value,
            progress_percentage=progress_percentage,
            is_achieved=is_achieved,
            data_source=data_source,
            raw_data_points=raw_data_points
        )
    
    def _calculate_weekly_progress(self, goal: Goal, target_date: date) -> ProgressSnapshot:
        """Calculate progress for weekly goals (average over the week)"""
        
        week_start, week_end = get_week_boundaries(target_date)
        week_dates = get_date_range(week_start, min(week_end, target_date))
        
        total_value = 0.0
        valid_days = 0
        total_raw_points = 0
        data_source = "none"
        
        # Calculate daily values and average them
        for check_date in week_dates:
            if goal.goal_type == GoalType.STEPS.value:
                daily_value, points = self._get_steps_for_date(check_date)
                data_source = "steps_data"
                
            elif goal.goal_type == GoalType.SLEEP_DURATION.value:
                daily_value, points = self._get_sleep_duration_for_date(check_date)
                data_source = "sleep_data"
                
            elif goal.goal_type == GoalType.WEIGHT_LOGGING.value:
                daily_value, points = self._get_weight_entries_for_date(check_date)
                data_source = "weight_data"
                
            elif goal.goal_type == GoalType.HRV_ENTRY.value:
                daily_value, points = self._get_hrv_entries_for_date(check_date)
                data_source = "manual_entries"
                
            elif goal.goal_type == GoalType.HEART_RATE_ZONE.value:
                daily_value, points = self._get_heart_rate_zone_minutes_for_date(check_date)
                data_source = "heart_rate_data"
            else:
                daily_value, points = 0.0, 0
            
            if daily_value > 0 or points > 0:
                total_value += daily_value
                valid_days += 1
                total_raw_points += points
        
        # Calculate weekly average
        actual_value = total_value / max(valid_days, 1) if valid_days > 0 else 0.0
        
        # For logging goals, count total entries rather than average
        if goal.goal_type in [GoalType.WEIGHT_LOGGING.value, GoalType.HRV_ENTRY.value]:
            actual_value = total_value
        
        progress_percentage = min((actual_value / goal.target_value) * 100, 100.0) if goal.target_value > 0 else 0.0
        is_achieved = actual_value >= goal.target_value
        
        return ProgressSnapshot(
            goal_id=goal.id,
            date=target_date,
            target_value=goal.target_value,
            actual_value=actual_value,
            progress_percentage=progress_percentage,
            is_achieved=is_achieved,
            data_source=data_source,
            raw_data_points=total_raw_points
        )
    
    def detect_achievements(self, goal: Goal, check_date: Optional[date] = None) -> List[GoalAchievement]:
        """
        Detect new goal achievements that haven't been recorded yet.
        
        Args:
            goal: Goal to check achievements for
            check_date: Date to check (defaults to today)
        
        Returns:
            List of new achievements detected
        """
        if not check_date:
            check_date = date.today()
        
        try:
            achievements = []
            
            if goal.frequency == GoalFrequency.DAILY.value:
                # Check daily achievement
                progress = self._calculate_daily_progress(goal, check_date)
                if progress.is_achieved:
                    # Check if achievement already recorded
                    existing = self._get_existing_achievement(goal.id, check_date)
                    if not existing:
                        achievement = GoalAchievement(
                            goal_id=goal.id,
                            achieved_date=check_date,
                            actual_value=progress.actual_value,
                            notes=f"Daily {goal.goal_type} goal achieved: {progress.actual_value}/{progress.target_value}"
                        )
                        achievements.append(achievement)
            
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                # Check if we're at the end of a complete week
                week_start, week_end = get_week_boundaries(check_date)
                
                if check_date >= week_end:  # Week is complete
                    progress = self._calculate_weekly_progress(goal, week_end)
                    if progress.is_achieved:
                        # Check if achievement already recorded for this week
                        existing = self._get_existing_achievement(goal.id, week_start)
                        if not existing:
                            achievement = GoalAchievement(
                                goal_id=goal.id,
                                achieved_date=week_start,  # Record achievement at week start
                                actual_value=progress.actual_value,
                                notes=f"Weekly {goal.goal_type} goal achieved: {progress.actual_value}/{progress.target_value}"
                            )
                            achievements.append(achievement)
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error detecting achievements for goal {goal.id}: {e}")
            return []
    
    def record_achievement(self, achievement: GoalAchievement) -> bool:
        """
        Record a goal achievement and update streak.
        
        Args:
            achievement: Achievement to record
        
        Returns:
            True if successful
        """
        try:
            # Insert achievement record
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO goal_achievements (goal_id, achieved_date, actual_value, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    achievement.goal_id,
                    achievement.achieved_date.isoformat(),
                    achievement.actual_value,
                    achievement.notes
                ))
                
                achievement.id = cursor.lastrowid
            
            # Update streak for this goal
            goal = self.db.get_goal(achievement.goal_id)
            if goal:
                updated_streak = self.streak_engine.calculate_streak_for_goal(goal, achievement.achieved_date)
                if updated_streak.id:
                    self.db.update_streak(updated_streak)
                else:
                    self.db.create_streak(updated_streak)
            
            logger.info(f"Recorded achievement {achievement.id} for goal {achievement.goal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording achievement: {e}")
            return False
    
    def update_goal_progress(self, goal: Goal, as_of_date: Optional[date] = None) -> None:
        """
        Update goal's current progress fields.
        
        Args:
            goal: Goal to update
            as_of_date: Date to calculate progress as of
        """
        try:
            progress = self.calculate_current_progress(goal, as_of_date)
            
            # Update goal's progress fields
            goal.current_progress = progress.actual_value
            goal.progress_percentage = progress.progress_percentage
            
            if goal.frequency == GoalFrequency.DAILY.value:
                goal.is_achieved_today = progress.is_achieved
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                goal.is_achieved_this_week = progress.is_achieved
            
            # Update in database
            self.db.update_goal(goal)
            
        except Exception as e:
            logger.error(f"Error updating goal progress for {goal.id}: {e}")
    
    def get_progress_history(self, goal: Goal, days_back: int = 30) -> List[ProgressSnapshot]:
        """
        Get historical progress data for a goal.
        
        Args:
            goal: Goal to get history for
            days_back: Number of days to include
        
        Returns:
            List of progress snapshots
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back - 1)
            
            history = []
            
            if goal.frequency == GoalFrequency.DAILY.value:
                # Daily progress for each day
                for check_date in get_date_range(start_date, end_date):
                    progress = self._calculate_daily_progress(goal, check_date)
                    history.append(progress)
            
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                # Weekly progress for each week
                current_date = end_date
                weeks_covered = 0
                
                while current_date >= start_date and weeks_covered < (days_back // 7 + 1):
                    week_start, week_end = get_week_boundaries(current_date)
                    progress = self._calculate_weekly_progress(goal, week_end)
                    history.append(progress)
                    
                    current_date = week_start - timedelta(days=1)
                    weeks_covered += 1
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting progress history for goal {goal.id}: {e}")
            return []
    
    def get_achievement_summary(self, goal: Goal, days_back: int = 30) -> Dict[str, Any]:
        """
        Get achievement summary statistics for a goal.
        
        Args:
            goal: Goal to analyze
            days_back: Number of days to include
        
        Returns:
            Summary statistics
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back - 1)
            
            # Get achievements in period
            achievements = self._get_achievements_in_range(goal.id, start_date, end_date)
            
            # Get progress history
            progress_history = self.get_progress_history(goal, days_back)
            
            # Calculate statistics
            total_possible = len(progress_history)
            total_achieved = len(achievements)
            achievement_rate = (total_achieved / total_possible * 100) if total_possible > 0 else 0
            
            # Calculate average progress
            avg_progress = sum(p.progress_percentage for p in progress_history) / max(len(progress_history), 1)
            avg_actual_value = sum(p.actual_value for p in progress_history) / max(len(progress_history), 1)
            
            # Find best day
            best_progress = max(progress_history, key=lambda p: p.actual_value) if progress_history else None
            
            return {
                "period_days": days_back,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_possible": total_possible,
                "total_achieved": total_achieved,
                "achievement_rate": achievement_rate,
                "average_progress_percentage": avg_progress,
                "average_actual_value": avg_actual_value,
                "target_value": goal.target_value,
                "best_day": {
                    "date": best_progress.date.isoformat(),
                    "value": best_progress.actual_value,
                    "percentage": best_progress.progress_percentage
                } if best_progress else None,
                "recent_achievements": [a.to_dict() for a in achievements[-5:]] if achievements else []
            }
            
        except Exception as e:
            logger.error(f"Error getting achievement summary for goal {goal.id}: {e}")
            return {"error": "Unable to generate summary"}
    
    def _get_steps_for_date(self, target_date: date) -> Tuple[float, int]:
        """Get total steps for a specific date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # First try daily summaries
                cursor.execute("""
                    SELECT value FROM daily_summaries 
                    WHERE date = ? AND metric = 'steps'
                """, (target_date.isoformat(),))
                
                row = cursor.fetchone()
                if row:
                    return float(row[0]), 1
                
                # Fall back to raw points
                start_time = target_date.isoformat() + "T00:00:00"
                end_time = (target_date + timedelta(days=1)).isoformat() + "T00:00:00"
                
                cursor.execute("""
                    SELECT SUM(value), COUNT(*) FROM raw_points 
                    WHERE metric = 'steps' AND start_time >= ? AND start_time < ?
                """, (start_time, end_time))
                
                row = cursor.fetchone()
                if row and row[0]:
                    return float(row[0]), int(row[1])
                
                return 0.0, 0
                
        except Exception as e:
            logger.error(f"Error getting steps for {target_date}: {e}")
            return 0.0, 0
    
    def _get_sleep_duration_for_date(self, target_date: date) -> Tuple[float, int]:
        """Get sleep duration for a specific date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check daily summaries first
                cursor.execute("""
                    SELECT value FROM daily_summaries 
                    WHERE date = ? AND metric = 'sleep'
                """, (target_date.isoformat(),))
                
                row = cursor.fetchone()
                if row:
                    # Convert minutes to hours
                    return float(row[0]) / 60.0, 1
                
                # Fall back to raw sleep data
                start_time = (target_date - timedelta(days=1)).isoformat() + "T18:00:00"
                end_time = (target_date + timedelta(days=1)).isoformat() + "T12:00:00"
                
                cursor.execute("""
                    SELECT SUM(value), COUNT(*) FROM raw_points 
                    WHERE metric = 'sleep' AND start_time >= ? AND start_time < ?
                """, (start_time, end_time))
                
                row = cursor.fetchone()
                if row and row[0]:
                    # Convert minutes to hours
                    return float(row[0]) / 60.0, int(row[1])
                
                return 0.0, 0
                
        except Exception as e:
            logger.error(f"Error getting sleep for {target_date}: {e}")
            return 0.0, 0
    
    def _get_weight_entries_for_date(self, target_date: date) -> Tuple[float, int]:
        """Get weight entries count for a specific date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM manual_entries 
                    WHERE date = ? AND metric IN ('weight', 'body_weight')
                """, (target_date.isoformat(),))
                
                row = cursor.fetchone()
                if row:
                    return float(row[0]), int(row[0])
                
                return 0.0, 0
                
        except Exception as e:
            logger.error(f"Error getting weight entries for {target_date}: {e}")
            return 0.0, 0
    
    def _get_hrv_entries_for_date(self, target_date: date) -> Tuple[float, int]:
        """Get HRV entries count for a specific date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM manual_entries 
                    WHERE date = ? AND metric = 'hrv'
                """, (target_date.isoformat(),))
                
                row = cursor.fetchone()
                if row:
                    return float(row[0]), int(row[0])
                
                return 0.0, 0
                
        except Exception as e:
            logger.error(f"Error getting HRV entries for {target_date}: {e}")
            return 0.0, 0
    
    def _get_heart_rate_zone_minutes_for_date(self, target_date: date) -> Tuple[float, int]:
        """Get heart rate zone minutes for a specific date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                start_time = target_date.isoformat() + "T00:00:00"
                end_time = (target_date + timedelta(days=1)).isoformat() + "T00:00:00"
                
                # Sum all heart rate zone minutes (zones 3-5 typically)
                cursor.execute("""
                    SELECT SUM(value), COUNT(*) FROM raw_points 
                    WHERE metric LIKE 'heart_rate_zone%' AND start_time >= ? AND start_time < ?
                """, (start_time, end_time))
                
                row = cursor.fetchone()
                if row and row[0]:
                    return float(row[0]), int(row[1])
                
                return 0.0, 0
                
        except Exception as e:
            logger.error(f"Error getting heart rate zones for {target_date}: {e}")
            return 0.0, 0
    
    def _get_existing_achievement(self, goal_id: int, achieved_date: date) -> Optional[GoalAchievement]:
        """Check if achievement already exists for date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM goal_achievements 
                    WHERE goal_id = ? AND achieved_date = ?
                """, (goal_id, achieved_date.isoformat()))
                
                row = cursor.fetchone()
                if row:
                    return GoalAchievement(
                        id=row[0],
                        goal_id=row[1],
                        achieved_date=datetime.fromisoformat(row[2]).date(),
                        actual_value=row[3],
                        notes=row[4]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error checking existing achievement: {e}")
            return None
    
    def _get_achievements_in_range(self, goal_id: int, start_date: date, end_date: date) -> List[GoalAchievement]:
        """Get achievements in date range"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM goal_achievements 
                    WHERE goal_id = ? AND achieved_date >= ? AND achieved_date <= ?
                    ORDER BY achieved_date ASC
                """, (goal_id, start_date.isoformat(), end_date.isoformat()))
                
                achievements = []
                for row in cursor.fetchall():
                    achievement = GoalAchievement(
                        id=row[0],
                        goal_id=row[1],
                        achieved_date=datetime.fromisoformat(row[2]).date(),
                        actual_value=row[3],
                        notes=row[4]
                    )
                    achievements.append(achievement)
                
                return achievements
                
        except Exception as e:
            logger.error(f"Error getting achievements in range: {e}")
            return []
    
    def run_achievement_detection(self, check_date: Optional[date] = None) -> Dict[str, int]:
        """
        Run achievement detection for all active goals.
        
        Args:
            check_date: Date to check achievements for (defaults to today)
        
        Returns:
            Summary of achievements detected
        """
        if not check_date:
            check_date = date.today()
        
        summary = {
            "goals_checked": 0,
            "achievements_detected": 0,
            "achievements_recorded": 0,
            "errors": 0
        }
        
        try:
            # Get all active goals
            active_goals = self.db.get_goals(status="active")
            
            for goal in active_goals:
                try:
                    summary["goals_checked"] += 1
                    
                    # Detect achievements
                    achievements = self.detect_achievements(goal, check_date)
                    summary["achievements_detected"] += len(achievements)
                    
                    # Record new achievements
                    for achievement in achievements:
                        if self.record_achievement(achievement):
                            summary["achievements_recorded"] += 1
                        else:
                            summary["errors"] += 1
                    
                    # Update goal progress
                    self.update_goal_progress(goal, check_date)
                    
                except Exception as e:
                    logger.error(f"Error processing goal {goal.id}: {e}")
                    summary["errors"] += 1
            
            logger.info(f"Achievement detection complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in achievement detection: {e}")
            summary["errors"] += 1
            return summary