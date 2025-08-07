"""
Streak Calculation Engine - Health Tracker
Core logic for streak tracking, freeze tokens, and consecutive achievement calculation
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from ..database import DatabaseManager
from ..models.goals import Goal, Streak, FreezeToken, GoalAchievement, GoalFrequency

logger = logging.getLogger(__name__)


class StreakStatus(Enum):
    """Status of a streak"""
    ACTIVE = "active"
    AT_RISK = "at_risk"
    BROKEN = "broken"
    FROZEN = "frozen"


class StreakEngine:
    """Core engine for streak calculation and management"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def calculate_streak_for_goal(self, goal: Goal, as_of_date: Optional[date] = None) -> Streak:
        """
        Calculate current streak status for a goal.
        
        Args:
            goal: Goal to calculate streak for
            as_of_date: Date to calculate streak as of (defaults to today)
        
        Returns:
            Updated Streak object with current status
        """
        if not as_of_date:
            as_of_date = date.today()
        
        try:
            # Get existing streak or create new one
            streak = self.db.get_streak(goal.id)
            if not streak:
                streak = Streak(goal_id=goal.id, current_count=0, best_count=0)
            
            # Get all achievements for this goal
            achievements = self._get_achievements_for_goal(goal.id)
            
            if goal.frequency == GoalFrequency.DAILY.value:
                return self._calculate_daily_streak(goal, streak, achievements, as_of_date)
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                return self._calculate_weekly_streak(goal, streak, achievements, as_of_date)
            else:
                logger.warning(f"Unknown frequency for goal {goal.id}: {goal.frequency}")
                return streak
                
        except Exception as e:
            logger.error(f"Error calculating streak for goal {goal.id}: {e}")
            raise
    
    def _calculate_daily_streak(self, goal: Goal, streak: Streak, 
                               achievements: List[GoalAchievement], as_of_date: date) -> Streak:
        """Calculate streak for daily goals"""
        
        # Filter achievements that meet the goal target
        successful_achievements = [
            a for a in achievements 
            if a.actual_value >= goal.target_value and a.achieved_date <= as_of_date
        ]
        
        if not successful_achievements:
            # No achievements yet
            streak.current_count = 0
            streak.last_achieved_date = None
            streak.is_active = True
            return streak
        
        # Sort achievements by date
        successful_achievements.sort(key=lambda a: a.achieved_date)
        
        # Find the longest current streak ending on or before as_of_date
        current_streak_count = 0
        current_streak_end = None
        
        # Work backwards from as_of_date to find current streak
        check_date = as_of_date
        
        while True:
            # Check if there's an achievement on check_date
            achievement_on_date = next(
                (a for a in successful_achievements if a.achieved_date == check_date), 
                None
            )
            
            if achievement_on_date:
                current_streak_count += 1
                current_streak_end = check_date
                check_date -= timedelta(days=1)
            else:
                # No achievement on this date
                if current_streak_count == 0:
                    # Haven't started a streak yet, keep looking back
                    check_date -= timedelta(days=1)
                    # Don't look back more than 30 days
                    if (as_of_date - check_date).days > 30:
                        break
                else:
                    # Streak is broken, but check for freeze token
                    if self._can_use_freeze_token(streak, check_date):
                        # Freeze token available, continue streak
                        check_date -= timedelta(days=1)
                    else:
                        # Streak is broken
                        break
        
        # Update streak object
        streak.current_count = current_streak_count
        streak.last_achieved_date = current_streak_end
        
        # Update best count if current is better
        if current_streak_count > streak.best_count:
            streak.best_count = current_streak_count
        
        # Determine streak status
        if current_streak_count == 0:
            streak.is_active = True  # Ready to start
        elif current_streak_end == as_of_date:
            streak.is_active = True  # Active and current
        elif current_streak_end == as_of_date - timedelta(days=1):
            streak.is_active = True  # At risk but not broken yet
        else:
            # Check if freeze token can save it
            if self._can_use_freeze_token(streak, as_of_date - timedelta(days=1)):
                streak.is_active = False  # At risk, needs freeze token
            else:
                streak.is_active = False  # Broken
        
        return streak
    
    def _calculate_weekly_streak(self, goal: Goal, streak: Streak, 
                                achievements: List[GoalAchievement], as_of_date: date) -> Streak:
        """Calculate streak for weekly goals"""
        
        # Group achievements by week
        weekly_achievements = self._group_achievements_by_week(achievements, as_of_date)
        
        # Calculate weekly averages and check if they meet the goal
        successful_weeks = []
        for week_start, week_achievements in weekly_achievements.items():
            if week_achievements:
                avg_value = sum(a.actual_value for a in week_achievements) / len(week_achievements)
                if avg_value >= goal.target_value:
                    successful_weeks.append(week_start)
        
        successful_weeks.sort(reverse=True)  # Most recent first
        
        if not successful_weeks:
            streak.current_count = 0
            streak.last_achieved_date = None
            streak.is_active = True
            return streak
        
        # Calculate current streak of consecutive weeks
        current_week_start = self._get_week_start(as_of_date)
        current_streak_count = 0
        
        check_week = current_week_start
        while check_week in successful_weeks:
            current_streak_count += 1
            check_week -= timedelta(weeks=1)
        
        # Update streak object
        streak.current_count = current_streak_count
        streak.last_achieved_date = successful_weeks[0] if successful_weeks else None
        
        # Update best count if current is better
        if current_streak_count > streak.best_count:
            streak.best_count = current_streak_count
        
        # Weekly goals are less strict about "at risk" status
        streak.is_active = True
        
        return streak
    
    def apply_freeze_token(self, streak_id: int, missed_date: date) -> bool:
        """
        Apply a freeze token to preserve a streak.
        
        Args:
            streak_id: ID of the streak to preserve
            missed_date: Date when goal was missed
        
        Returns:
            True if freeze token was successfully applied
        """
        try:
            # Get available freeze tokens
            available_tokens = self.db.get_available_freeze_tokens(streak_id)
            
            if not available_tokens:
                logger.info(f"No freeze tokens available for streak {streak_id}")
                return False
            
            # Use the oldest available token
            token = available_tokens[0]
            success = self.db.use_freeze_token(token.id, missed_date)
            
            if success:
                logger.info(f"Applied freeze token {token.id} for streak {streak_id} on {missed_date}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying freeze token for streak {streak_id}: {e}")
            return False
    
    def issue_monthly_freeze_token(self, streak_id: int, issue_date: Optional[date] = None) -> Optional[FreezeToken]:
        """
        Issue a monthly freeze token for a streak.
        
        Args:
            streak_id: ID of the streak
            issue_date: Date to issue token (defaults to today)
        
        Returns:
            Created FreezeToken or None if failed
        """
        if not issue_date:
            issue_date = date.today()
        
        try:
            # Check if token already issued this month
            month_start = issue_date.replace(day=1)
            month_end = self._get_month_end(issue_date)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM freeze_tokens 
                    WHERE streak_id = ? AND issued_date >= ? AND issued_date <= ?
                """, (streak_id, month_start.isoformat(), month_end.isoformat()))
                
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    logger.info(f"Freeze token already issued this month for streak {streak_id}")
                    return None
            
            # Create and insert new token
            token = FreezeToken(
                streak_id=streak_id,
                issued_date=issue_date,
                expires_date=month_end
            )
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO freeze_tokens (streak_id, issued_date, expires_date, is_used)
                    VALUES (?, ?, ?, ?)
                """, (
                    token.streak_id,
                    token.issued_date.isoformat(),
                    token.expires_date.isoformat(),
                    token.is_used
                ))
                
                token.id = cursor.lastrowid
            
            logger.info(f"Issued freeze token {token.id} for streak {streak_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error issuing freeze token for streak {streak_id}: {e}")
            return None
    
    def get_streak_status(self, streak: Streak, as_of_date: Optional[date] = None) -> StreakStatus:
        """
        Get the current status of a streak.
        
        Args:
            streak: Streak to check status for
            as_of_date: Date to check status as of (defaults to today)
        
        Returns:
            Current StreakStatus
        """
        if not as_of_date:
            as_of_date = date.today()
        
        if not streak.is_active:
            return StreakStatus.BROKEN
        
        if not streak.last_achieved_date:
            return StreakStatus.ACTIVE
        
        days_since = (as_of_date - streak.last_achieved_date).days
        
        if days_since == 0:
            return StreakStatus.ACTIVE
        elif days_since == 1:
            return StreakStatus.AT_RISK
        elif days_since >= 2:
            # Check if freeze token was used
            available_tokens = self.db.get_available_freeze_tokens(streak.id)
            if available_tokens:
                return StreakStatus.AT_RISK  # Can still be saved
            else:
                return StreakStatus.BROKEN
        
        return StreakStatus.ACTIVE
    
    def get_streak_insights(self, streak: Streak, goal: Goal) -> Dict[str, Any]:
        """
        Get insights and statistics about a streak.
        
        Args:
            streak: Streak to analyze
            goal: Associated goal
        
        Returns:
            Dictionary with streak insights
        """
        try:
            insights = {
                "current_count": streak.current_count,
                "best_count": streak.best_count,
                "status": self.get_streak_status(streak).value,
                "is_personal_best": streak.current_count == streak.best_count and streak.current_count > 0,
                "days_since_last": streak.days_since_last_achievement,
                "freeze_tokens_available": len(self.db.get_available_freeze_tokens(streak.id)) if streak.id else 0,
                "freeze_tokens_used": streak.freeze_tokens_used
            }
            
            # Add status-specific insights
            status = self.get_streak_status(streak)
            
            if status == StreakStatus.AT_RISK:
                insights["risk_message"] = "Complete your goal today to maintain your streak!"
                insights["can_use_freeze_token"] = insights["freeze_tokens_available"] > 0
            
            elif status == StreakStatus.ACTIVE and streak.current_count > 0:
                insights["encouragement"] = f"Great job! You're on a {streak.current_count}-day streak."
                
                if streak.current_count == streak.best_count:
                    insights["milestone_message"] = "This is your personal best streak!"
            
            elif status == StreakStatus.BROKEN:
                insights["recovery_message"] = "Don't worry! Start a new streak today."
                insights["previous_best"] = streak.best_count
            
            # Calculate streak consistency (achievements vs possible days)
            if goal.start_date:
                days_since_start = (date.today() - goal.start_date).days + 1
                achievements = self._get_achievements_for_goal(goal.id)
                successful_days = len([a for a in achievements if a.actual_value >= goal.target_value])
                insights["consistency_percentage"] = (successful_days / max(days_since_start, 1)) * 100
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating streak insights: {e}")
            return {"error": "Unable to generate insights"}
    
    def _get_achievements_for_goal(self, goal_id: int) -> List[GoalAchievement]:
        """Get all achievements for a goal, sorted by date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM goal_achievements 
                    WHERE goal_id = ?
                    ORDER BY achieved_date ASC
                """, (goal_id,))
                
                achievements = []
                for row in cursor.fetchall():
                    achievement = GoalAchievement(
                        id=row[0],
                        goal_id=row[1],
                        achieved_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
                        actual_value=row[3],
                        notes=row[4]
                    )
                    achievements.append(achievement)
                
                return achievements
                
        except Exception as e:
            logger.error(f"Error getting achievements for goal {goal_id}: {e}")
            return []
    
    def _can_use_freeze_token(self, streak: Streak, missed_date: date) -> bool:
        """Check if freeze token can be used to preserve streak"""
        if not streak.id:
            return False
        
        available_tokens = self.db.get_available_freeze_tokens(streak.id)
        return len(available_tokens) > 0
    
    def _group_achievements_by_week(self, achievements: List[GoalAchievement], 
                                   as_of_date: date) -> Dict[date, List[GoalAchievement]]:
        """Group achievements by week (Monday-Sunday)"""
        weekly_groups = {}
        
        for achievement in achievements:
            if achievement.achieved_date <= as_of_date:
                week_start = self._get_week_start(achievement.achieved_date)
                
                if week_start not in weekly_groups:
                    weekly_groups[week_start] = []
                
                weekly_groups[week_start].append(achievement)
        
        return weekly_groups
    
    def _get_week_start(self, date_obj: date) -> date:
        """Get Monday of the week containing the given date"""
        return date_obj - timedelta(days=date_obj.weekday())
    
    def _get_month_end(self, date_obj: date) -> date:
        """Get last day of the month containing the given date"""
        if date_obj.month == 12:
            return date(date_obj.year + 1, 1, 1) - timedelta(days=1)
        else:
            return date(date_obj.year, date_obj.month + 1, 1) - timedelta(days=1)
    
    def update_all_streaks(self, as_of_date: Optional[date] = None) -> Dict[str, int]:
        """
        Update all streaks in the system.
        
        Args:
            as_of_date: Date to calculate streaks as of (defaults to today)
        
        Returns:
            Summary of updates performed
        """
        if not as_of_date:
            as_of_date = date.today()
        
        summary = {
            "updated": 0,
            "errors": 0,
            "tokens_issued": 0
        }
        
        try:
            # Get all active goals
            goals = self.db.get_goals(status="active")
            
            for goal in goals:
                try:
                    # Calculate current streak
                    updated_streak = self.calculate_streak_for_goal(goal, as_of_date)
                    
                    # Update in database
                    if updated_streak.id:
                        self.db.update_streak(updated_streak)
                    
                    # Issue monthly freeze token if needed
                    if self.issue_monthly_freeze_token(updated_streak.id, as_of_date):
                        summary["tokens_issued"] += 1
                    
                    summary["updated"] += 1
                    
                except Exception as e:
                    logger.error(f"Error updating streak for goal {goal.id}: {e}")
                    summary["errors"] += 1
            
            logger.info(f"Updated {summary['updated']} streaks, {summary['errors']} errors, "
                       f"{summary['tokens_issued']} tokens issued")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in update_all_streaks: {e}")
            summary["errors"] += 1
            return summary