"""
Goals Service - Health Tracker
Business logic for goal management, streak tracking, and achievement processing
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from ..database import DatabaseManager
from ..models.goals import Goal, Streak, FreezeToken, GoalAchievement, GoalType, GoalFrequency, GoalStatus

logger = logging.getLogger(__name__)


class GoalsService:
    """Service class for goals and streaks business logic"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    async def get_goals(self, status: Optional[str] = None, goal_type: Optional[str] = None, 
                       include_progress: bool = True) -> List[Goal]:
        """Get goals with optional filtering and progress calculation"""
        try:
            goals = self.db.get_goals(status=status, goal_type=goal_type)
            
            if include_progress:
                # Calculate current progress for each goal
                for goal in goals:
                    await self._calculate_goal_progress(goal)
            
            return goals
            
        except Exception as e:
            logger.error(f"Error in get_goals: {e}")
            raise
    
    async def get_goal(self, goal_id: int, include_progress: bool = True) -> Optional[Goal]:
        """Get a specific goal with progress calculation"""
        try:
            goal = self.db.get_goal(goal_id)
            
            if goal and include_progress:
                await self._calculate_goal_progress(goal)
            
            return goal
            
        except Exception as e:
            logger.error(f"Error in get_goal: {e}")
            raise
    
    async def create_goal(self, goal_data: Dict[str, Any]) -> Goal:
        """Create a new goal with validation"""
        try:
            # Create goal object from data
            goal = Goal(
                goal_type=goal_data["goal_type"],
                target_value=float(goal_data["target_value"]),
                frequency=goal_data["frequency"],
                description=goal_data.get("description"),
                start_date=date.today(),
                status=GoalStatus.ACTIVE.value
            )
            
            # Check for existing active goal of same type and frequency
            existing_goals = self.db.get_goals(
                status=GoalStatus.ACTIVE.value, 
                goal_type=goal.goal_type
            )
            
            for existing_goal in existing_goals:
                if existing_goal.frequency == goal.frequency:
                    raise ValueError(f"Active {goal.frequency} goal for {goal.goal_type} already exists")
            
            # Create goal in database
            goal_id = self.db.create_goal(goal)
            goal.id = goal_id
            
            # Initial progress calculation
            await self._calculate_goal_progress(goal)
            
            logger.info(f"Created goal {goal_id}: {goal.display_name} - {goal.target_value} {goal.unit}")
            
            return goal
            
        except Exception as e:
            logger.error(f"Error in create_goal: {e}")
            raise
    
    async def update_goal(self, goal_id: int, goal_data: Dict[str, Any]) -> Goal:
        """Update an existing goal"""
        try:
            goal = self.db.get_goal(goal_id)
            if not goal:
                raise ValueError("Goal not found")
            
            # Update fields if provided
            if "target_value" in goal_data:
                goal.target_value = float(goal_data["target_value"])
            
            if "description" in goal_data:
                goal.description = goal_data["description"]
            
            if "status" in goal_data:
                goal.status = goal_data["status"]
            
            if "end_date" in goal_data:
                if goal_data["end_date"]:
                    goal.end_date = datetime.fromisoformat(goal_data["end_date"]).date()
                else:
                    goal.end_date = None
            
            # Update in database
            success = self.db.update_goal(goal)
            if not success:
                raise ValueError("Failed to update goal in database")
            
            # Recalculate progress
            await self._calculate_goal_progress(goal)
            
            logger.info(f"Updated goal {goal_id}")
            
            return goal
            
        except Exception as e:
            logger.error(f"Error in update_goal: {e}")
            raise
    
    async def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal and all associated data"""
        try:
            success = self.db.delete_goal(goal_id)
            
            if success:
                logger.info(f"Deleted goal {goal_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in delete_goal: {e}")
            raise
    
    async def get_streak(self, goal_id: int) -> Optional[Streak]:
        """Get streak for a goal"""
        try:
            return self.db.get_streak(goal_id)
            
        except Exception as e:
            logger.error(f"Error in get_streak: {e}")
            raise
    
    async def create_streak(self, goal_id: int) -> Streak:
        """Create initial streak record for a goal"""
        try:
            streak = Streak(
                goal_id=goal_id,
                current_count=0,
                best_count=0,
                is_active=True
            )
            
            # The database trigger will handle creation automatically
            # when a goal is created, but this is a fallback
            return streak
            
        except Exception as e:
            logger.error(f"Error in create_streak: {e}")
            raise
    
    async def get_achievements(self, goal_id: int, limit: int = 50, offset: int = 0) -> List[GoalAchievement]:
        """Get achievement history for a goal"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM goal_achievements 
                    WHERE goal_id = ?
                    ORDER BY achieved_date DESC
                    LIMIT ? OFFSET ?
                """, (goal_id, limit, offset))
                
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
            logger.error(f"Error in get_achievements: {e}")
            raise
    
    async def record_achievement(self, goal_id: int, achievement_data: Dict[str, Any]) -> GoalAchievement:
        """Record a goal achievement and update streak"""
        try:
            # Create achievement record
            achieved_date = date.today()
            if "achieved_date" in achievement_data:
                achieved_date = datetime.fromisoformat(achievement_data["achieved_date"]).date()
            
            achievement = GoalAchievement(
                goal_id=goal_id,
                achieved_date=achieved_date,
                actual_value=float(achievement_data["actual_value"]),
                notes=achievement_data.get("notes")
            )
            
            # Record in database
            achievement_id = self.db.record_goal_achievement(achievement)
            achievement.id = achievement_id
            
            # Update streak if achievement meets goal target
            goal = self.db.get_goal(goal_id)
            if goal and achievement.actual_value >= goal.target_value:
                await self._update_streak_for_achievement(goal, achieved_date)
            
            logger.info(f"Recorded achievement for goal {goal_id}: {achievement.actual_value}")
            
            return achievement
            
        except Exception as e:
            logger.error(f"Error in record_achievement: {e}")
            raise
    
    async def get_freeze_tokens(self, goal_id: int) -> List[FreezeToken]:
        """Get available freeze tokens for a goal"""
        try:
            streak = self.db.get_streak(goal_id)
            if not streak:
                return []
            
            return self.db.get_available_freeze_tokens(streak.id)
            
        except Exception as e:
            logger.error(f"Error in get_freeze_tokens: {e}")
            raise
    
    async def use_freeze_token(self, token_id: int, used_date: date) -> bool:
        """Use a freeze token to preserve streak"""
        try:
            success = self.db.use_freeze_token(token_id, used_date)
            
            if success:
                logger.info(f"Used freeze token {token_id} on {used_date}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in use_freeze_token: {e}")
            raise
    
    async def get_goals_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all goals"""
        try:
            active_goals = self.db.get_goals(status=GoalStatus.ACTIVE.value)
            
            # Calculate summary statistics
            total_goals = len(active_goals)
            goals_by_type = {}
            total_current_streaks = 0
            total_best_streaks = 0
            
            for goal in active_goals:
                # Count by type
                if goal.goal_type not in goals_by_type:
                    goals_by_type[goal.goal_type] = 0
                goals_by_type[goal.goal_type] += 1
                
                # Get streak info
                streak = self.db.get_streak(goal.id)
                if streak:
                    total_current_streaks += streak.current_count
                    total_best_streaks += streak.best_count
            
            # Calculate today's achievements
            today = date.today()
            achieved_today = 0
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM goal_achievements 
                    WHERE achieved_date = ?
                """, (today.isoformat(),))
                achieved_today = cursor.fetchone()[0]
            
            return {
                "total_active_goals": total_goals,
                "goals_by_type": goals_by_type,
                "total_current_streaks": total_current_streaks,
                "average_current_streak": total_current_streaks / max(total_goals, 1),
                "total_best_streaks": total_best_streaks,
                "achieved_today": achieved_today,
                "summary_date": today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in get_goals_summary: {e}")
            raise
    
    async def _calculate_goal_progress(self, goal: Goal) -> None:
        """Calculate current progress for a goal"""
        try:
            today = date.today()
            
            if goal.frequency == GoalFrequency.DAILY.value:
                # Check today's achievement
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT actual_value FROM goal_achievements 
                        WHERE goal_id = ? AND achieved_date = ?
                        ORDER BY actual_value DESC LIMIT 1
                    """, (goal.id, today.isoformat()))
                    
                    row = cursor.fetchone()
                    if row:
                        goal.current_progress = row[0]
                        goal.progress_percentage = min(100, (goal.current_progress / goal.target_value) * 100)
                        goal.is_achieved_today = goal.current_progress >= goal.target_value
                    else:
                        goal.current_progress = 0
                        goal.progress_percentage = 0
                        goal.is_achieved_today = False
            
            elif goal.frequency == GoalFrequency.WEEKLY.value:
                # Check this week's achievements
                week_start = today - timedelta(days=today.weekday())
                
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT AVG(actual_value), COUNT(*) FROM goal_achievements 
                        WHERE goal_id = ? AND achieved_date >= ? AND achieved_date <= ?
                    """, (goal.id, week_start.isoformat(), today.isoformat()))
                    
                    row = cursor.fetchone()
                    if row and row[0]:
                        goal.current_progress = row[0]
                        goal.progress_percentage = min(100, (goal.current_progress / goal.target_value) * 100)
                        goal.is_achieved_this_week = goal.current_progress >= goal.target_value
                    else:
                        goal.current_progress = 0
                        goal.progress_percentage = 0
                        goal.is_achieved_this_week = False
                        
        except Exception as e:
            logger.error(f"Error calculating progress for goal {goal.id}: {e}")
            # Don't raise, just log the error and continue with zero progress
            goal.current_progress = 0
            goal.progress_percentage = 0
    
    async def _update_streak_for_achievement(self, goal: Goal, achieved_date: date) -> None:
        """Update streak when goal is achieved"""
        try:
            streak = self.db.get_streak(goal.id)
            if not streak:
                return
            
            # Check if this continues the streak
            if goal.frequency == GoalFrequency.DAILY.value:
                # Daily goal: check if achieved yesterday or today
                expected_date = achieved_date - timedelta(days=1)
                
                if (streak.last_achieved_date == expected_date or 
                    streak.last_achieved_date == achieved_date):
                    # Continue streak
                    if streak.last_achieved_date != achieved_date:  # Avoid double counting
                        streak.current_count += 1
                        streak.last_achieved_date = achieved_date
                else:
                    # Reset streak (unless freeze token is available)
                    available_tokens = self.db.get_available_freeze_tokens(streak.id)
                    if available_tokens and streak.last_achieved_date:
                        # Could use freeze token, but don't auto-use it
                        streak.is_active = False  # Mark as at risk
                    else:
                        # Reset streak
                        streak.current_count = 1
                        streak.last_achieved_date = achieved_date
                        streak.is_active = True
            
            # Update streak in database
            self.db.update_streak(streak)
            
        except Exception as e:
            logger.error(f"Error updating streak for goal {goal.id}: {e}")
            # Don't raise, as achievement was already recorded