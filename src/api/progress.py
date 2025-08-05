"""
Progress Tracking API - Health Tracker
REST endpoints for goal progress tracking and achievement management
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from ..services.progress_tracker import ProgressTracker, ProgressSnapshot
from ..database import DatabaseManager
from ..models.goals import Goal, GoalAchievement
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/progress", tags=["progress"])


def get_progress_tracker() -> ProgressTracker:
    """Dependency to get progress tracker instance"""
    return ProgressTracker()


def get_database() -> DatabaseManager:
    """Dependency to get database instance"""
    return DatabaseManager()


@router.get("/goal/{goal_id}/current", response_model=Dict[str, Any])
async def get_current_progress(
    goal_id: int,
    as_of_date: Optional[str] = Query(None, description="Date to calculate progress as of (YYYY-MM-DD)"),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Get current progress for a specific goal"""
    try:
        # Get the goal
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Parse date if provided
        target_date = None
        if as_of_date:
            try:
                target_date = datetime.fromisoformat(as_of_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Calculate progress
        progress = progress_tracker.calculate_current_progress(goal, target_date)
        
        return {
            "goal": goal.to_dict(),
            "progress": progress.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating progress: {str(e)}")


@router.get("/goal/{goal_id}/history", response_model=List[Dict[str, Any]])
async def get_progress_history(
    goal_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include"),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Get historical progress data for a goal"""
    try:
        # Get the goal
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Get progress history
        history = progress_tracker.get_progress_history(goal, days_back)
        
        return [progress.to_dict() for progress in history]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting progress history: {str(e)}")


@router.get("/goal/{goal_id}/summary", response_model=Dict[str, Any])
async def get_achievement_summary(
    goal_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include"),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Get achievement summary statistics for a goal"""
    try:
        # Get the goal
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Get achievement summary
        summary = progress_tracker.get_achievement_summary(goal, days_back)
        
        return {
            "goal": goal.to_dict(),
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting achievement summary: {str(e)}")


@router.get("/achievements/{goal_id}", response_model=List[Dict[str, Any]])
async def get_goal_achievements(
    goal_id: int,
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of achievements to return"),
    db: DatabaseManager = Depends(get_database)
):
    """Get achievements for a specific goal"""
    try:
        # Validate goal exists
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Parse date filters
        start_filter = None
        end_filter = None
        
        if start_date:
            try:
                start_filter = datetime.fromisoformat(start_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_filter = datetime.fromisoformat(end_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        # Get achievements from database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM goal_achievements WHERE goal_id = ?"
            params = [goal_id]
            
            if start_filter:
                query += " AND achieved_date >= ?"
                params.append(start_filter.isoformat())
            
            if end_filter:
                query += " AND achieved_date <= ?"
                params.append(end_filter.isoformat())
            
            query += " ORDER BY achieved_date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            achievements = []
            for row in cursor.fetchall():
                achievement = GoalAchievement(
                    id=row[0],
                    goal_id=row[1],
                    achieved_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
                    actual_value=row[3],
                    notes=row[4]
                )
                achievements.append(achievement.to_dict())
            
            return achievements
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting achievements: {str(e)}")


@router.post("/detect", response_model=Dict[str, Any])
async def detect_achievements(
    check_date: Optional[str] = Query(None, description="Date to check achievements for (YYYY-MM-DD)"),
    goal_id: Optional[int] = Query(None, description="Specific goal ID to check (optional)"),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Detect and record new goal achievements"""
    try:
        # Parse check date
        target_date = None
        if check_date:
            try:
                target_date = datetime.fromisoformat(check_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = date.today()
        
        if goal_id:
            # Check specific goal
            goal = db.get_goal(goal_id)
            if not goal:
                raise HTTPException(status_code=404, detail="Goal not found")
            
            # Detect achievements for this goal
            achievements = progress_tracker.detect_achievements(goal, target_date)
            
            # Record achievements
            recorded_count = 0
            for achievement in achievements:
                if progress_tracker.record_achievement(achievement):
                    recorded_count += 1
            
            # Update goal progress
            progress_tracker.update_goal_progress(goal, target_date)
            
            return {
                "check_date": target_date.isoformat(),
                "goal_id": goal_id,
                "achievements_detected": len(achievements),
                "achievements_recorded": recorded_count,
                "achievements": [a.to_dict() for a in achievements]
            }
        else:
            # Check all active goals
            summary = progress_tracker.run_achievement_detection(target_date)
            summary["check_date"] = target_date.isoformat()
            return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting achievements: {str(e)}")


@router.post("/goal/{goal_id}/manual-achievement", response_model=Dict[str, Any])
async def record_manual_achievement(
    goal_id: int,
    achievement_data: Dict[str, Any],
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Manually record a goal achievement"""
    try:
        # Validate goal exists
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Parse achievement data
        achieved_date_str = achievement_data.get("achieved_date")
        if not achieved_date_str:
            achieved_date = date.today()
        else:
            try:
                achieved_date = datetime.fromisoformat(achieved_date_str).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid achieved_date format. Use YYYY-MM-DD")
        
        actual_value = achievement_data.get("actual_value", 0.0)
        if not isinstance(actual_value, (int, float)) or actual_value < 0:
            raise HTTPException(status_code=400, detail="actual_value must be a non-negative number")
        
        notes = achievement_data.get("notes", "Manual achievement entry")
        
        # Create achievement record
        achievement = GoalAchievement(
            goal_id=goal_id,
            achieved_date=achieved_date,
            actual_value=float(actual_value),
            notes=str(notes)
        )
        
        # Check if achievement already exists
        existing = progress_tracker._get_existing_achievement(goal_id, achieved_date)
        if existing:
            raise HTTPException(status_code=409, detail="Achievement already exists for this date")
        
        # Record the achievement
        success = progress_tracker.record_achievement(achievement)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to record achievement")
        
        # Update goal progress
        progress_tracker.update_goal_progress(goal, achieved_date)
        
        return {
            "message": "Achievement recorded successfully",
            "achievement": achievement.to_dict(),
            "goal": goal.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording manual achievement: {str(e)}")


@router.delete("/achievement/{achievement_id}", response_model=Dict[str, Any])
async def delete_achievement(
    achievement_id: int,
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Delete a goal achievement"""
    try:
        # Get the achievement to find associated goal
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT goal_id FROM goal_achievements WHERE id = ?", (achievement_id,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Achievement not found")
            
            goal_id = row[0]
            
            # Delete the achievement
            cursor.execute("DELETE FROM goal_achievements WHERE id = ?", (achievement_id,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Achievement not found")
        
        # Recalculate streak for the associated goal
        goal = db.get_goal(goal_id)
        if goal:
            updated_streak = progress_tracker.streak_engine.calculate_streak_for_goal(goal)
            if updated_streak.id:
                db.update_streak(updated_streak)
            
            # Update goal progress
            progress_tracker.update_goal_progress(goal)
        
        return {
            "message": "Achievement deleted successfully",
            "achievement_id": achievement_id,
            "goal_id": goal_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting achievement: {str(e)}")


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_progress_dashboard(
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Get progress dashboard data for all active goals"""
    try:
        active_goals = db.get_goals(status="active")
        
        dashboard_data = {
            "total_goals": len(active_goals),
            "goals_achieved_today": 0,
            "goals_achieved_this_week": 0,
            "current_streaks": 0,
            "goals": []
        }
        
        for goal in active_goals:
            try:
                # Get current progress
                current_progress = progress_tracker.calculate_current_progress(goal)
                
                # Get streak info
                streak = db.get_streak(goal.id)
                
                # Get recent achievements
                recent_achievements = progress_tracker._get_achievements_in_range(
                    goal.id, 
                    date.today() - timedelta(days=7), 
                    date.today()
                )
                
                goal_data = goal.to_dict()
                goal_data.update({
                    "current_progress": current_progress.to_dict(),
                    "streak": streak.to_dict() if streak else None,
                    "recent_achievements_count": len(recent_achievements)
                })
                
                dashboard_data["goals"].append(goal_data)
                
                # Update counters
                if current_progress.is_achieved and current_progress.date == date.today():
                    dashboard_data["goals_achieved_today"] += 1
                
                if goal.is_achieved_this_week:
                    dashboard_data["goals_achieved_this_week"] += 1
                
                if streak and streak.is_active and streak.current_count > 0:
                    dashboard_data["current_streaks"] += 1
                    
            except Exception as e:
                # Log error but continue with other goals
                logger.error(f"Error processing goal {goal.id} for dashboard: {e}")
                continue
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting progress dashboard: {str(e)}")


@router.post("/update-all", response_model=Dict[str, Any])
async def update_all_progress(
    as_of_date: Optional[str] = Query(None, description="Date to update progress as of (YYYY-MM-DD)"),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker),
    db: DatabaseManager = Depends(get_database)
):
    """Update progress for all active goals"""
    try:
        # Parse date if provided
        target_date = None
        if as_of_date:
            try:
                target_date = datetime.fromisoformat(as_of_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = date.today()
        
        # Get all active goals
        active_goals = db.get_goals(status="active")
        
        summary = {
            "update_date": target_date.isoformat(),
            "goals_processed": 0,
            "goals_updated": 0,
            "errors": 0
        }
        
        for goal in active_goals:
            try:
                summary["goals_processed"] += 1
                progress_tracker.update_goal_progress(goal, target_date)
                summary["goals_updated"] += 1
                
            except Exception as e:
                logger.error(f"Error updating progress for goal {goal.id}: {e}")
                summary["errors"] += 1
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating progress: {str(e)}")