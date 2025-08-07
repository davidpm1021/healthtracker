"""
Progress Update Job - Health Tracker
Background job for updating goal progress and detecting achievements
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any

from ..services.progress_tracker import ProgressTracker
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class ProgressUpdateJob:
    """Background job for progress tracking"""
    
    def __init__(self):
        self.progress_tracker = ProgressTracker()
        self.db = DatabaseManager()
    
    def run_daily_update(self, target_date: date = None) -> Dict[str, Any]:
        """
        Run daily progress update and achievement detection.
        
        Args:
            target_date: Date to update progress for (defaults to today)
        
        Returns:
            Summary of updates performed
        """
        if not target_date:
            target_date = date.today()
        
        logger.info(f"Starting daily progress update for {target_date}")
        
        try:
            # Run achievement detection for all goals
            achievement_summary = self.progress_tracker.run_achievement_detection(target_date)
            
            # Update streak calculations
            streak_summary = self.progress_tracker.streak_engine.update_all_streaks(target_date)
            
            # Issue monthly freeze tokens
            freeze_token_summary = self._issue_monthly_tokens(target_date)
            
            summary = {
                "update_date": target_date.isoformat(),
                "achievements": achievement_summary,
                "streaks": streak_summary,
                "freeze_tokens": freeze_token_summary,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Daily progress update completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in daily progress update: {e}")
            return {
                "update_date": target_date.isoformat(),
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_weekly_cleanup(self) -> Dict[str, Any]:
        """
        Run weekly cleanup tasks.
        
        Returns:
            Summary of cleanup performed
        """
        logger.info("Starting weekly progress cleanup")
        
        try:
            # Clean up expired freeze tokens
            from ..services.freeze_tokens import FreezeTokenManager
            token_manager = FreezeTokenManager()
            expired_tokens = token_manager.expire_old_tokens()
            
            # Archive very old achievements (optional)
            archived_achievements = self._archive_old_achievements()
            
            summary = {
                "expired_tokens": expired_tokens,
                "archived_achievements": archived_achievements,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Weekly cleanup completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in weekly cleanup: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def backfill_progress(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Backfill progress data for a date range.
        
        Args:
            start_date: Start date for backfill
            end_date: End date for backfill
        
        Returns:
            Summary of backfill operation
        """
        logger.info(f"Starting progress backfill from {start_date} to {end_date}")
        
        try:
            summary = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days_processed": 0,
                "achievements_detected": 0,
                "achievements_recorded": 0,
                "streaks_updated": 0,
                "errors": 0
            }
            
            current_date = start_date
            while current_date <= end_date:
                try:
                    # Run achievement detection for this date
                    daily_summary = self.progress_tracker.run_achievement_detection(current_date)
                    
                    summary["days_processed"] += 1
                    summary["achievements_detected"] += daily_summary.get("achievements_detected", 0)
                    summary["achievements_recorded"] += daily_summary.get("achievements_recorded", 0)
                    summary["errors"] += daily_summary.get("errors", 0)
                    
                    # Update streaks for this date
                    streak_summary = self.progress_tracker.streak_engine.update_all_streaks(current_date)
                    summary["streaks_updated"] += streak_summary.get("updated", 0)
                    
                except Exception as e:
                    logger.error(f"Error processing date {current_date}: {e}")
                    summary["errors"] += 1
                
                current_date += timedelta(days=1)
            
            summary["status"] = "completed"
            summary["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"Progress backfill completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in progress backfill: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _issue_monthly_tokens(self, target_date: date) -> Dict[str, Any]:
        """Issue monthly freeze tokens if needed"""
        try:
            from ..services.freeze_tokens import FreezeTokenManager
            token_manager = FreezeTokenManager()
            
            # Only issue tokens on the first day of the month
            if target_date.day == 1:
                return token_manager.issue_monthly_tokens(target_date)
            else:
                return {
                    "tokens_issued": 0,
                    "message": "Not first day of month, skipping token issuance"
                }
                
        except Exception as e:
            logger.error(f"Error issuing monthly tokens: {e}")
            return {
                "tokens_issued": 0,
                "error": str(e)
            }
    
    def _archive_old_achievements(self, days_old: int = 365) -> int:
        """Archive achievements older than specified days"""
        try:
            cutoff_date = date.today() - timedelta(days=days_old)
            
            # For now, we'll just count old achievements
            # In a real implementation, you might move them to an archive table
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM goal_achievements 
                    WHERE achieved_date < ?
                """, (cutoff_date.isoformat(),))
                
                old_count = cursor.fetchone()[0]
                
                # Optionally delete or archive very old records
                # cursor.execute("DELETE FROM goal_achievements WHERE achieved_date < ?", (cutoff_date.isoformat(),))
                
                return old_count
                
        except Exception as e:
            logger.error(f"Error archiving old achievements: {e}")
            return 0


# Job registration functions for the scheduler
def register_progress_jobs():
    """Register progress tracking jobs with the scheduler"""
    from ..scheduler import scheduler, get_scheduler
    
    # Daily progress update at 11:30 PM
    @scheduler.scheduled_job('cron', hour=23, minute=30, id='daily_progress_update')
    def daily_progress_update():
        """Daily progress update job"""
        job = ProgressUpdateJob()
        return job.run_daily_update()
    
    # Weekly cleanup on Sundays at 2:00 AM
    @scheduler.scheduled_job('cron', day_of_week='sun', hour=2, minute=0, id='weekly_progress_cleanup')
    def weekly_progress_cleanup():
        """Weekly progress cleanup job"""
        job = ProgressUpdateJob()
        return job.run_weekly_cleanup()
    
    logger.info("Progress tracking jobs registered")


def run_manual_progress_update(target_date: str = None) -> Dict[str, Any]:
    """
    Manually run progress update for a specific date.
    
    Args:
        target_date: Date string in YYYY-MM-DD format
    
    Returns:
        Update summary
    """
    job = ProgressUpdateJob()
    
    if target_date:
        try:
            parsed_date = datetime.fromisoformat(target_date).date()
        except ValueError:
            return {
                "status": "error",
                "error": "Invalid date format. Use YYYY-MM-DD"
            }
    else:
        parsed_date = date.today()
    
    return job.run_daily_update(parsed_date)