"""
Goals Management API - Health Tracker
REST endpoints for goal configuration, tracking, and streak management
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging

from ..database import DatabaseManager
from ..models.goals import Goal, Streak, FreezeToken, GoalAchievement, GoalType, GoalFrequency, GoalStatus
from ..services.goals_service import GoalsService

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_goals(
    status: Optional[str] = Query(None, description="Filter by goal status (active, paused, completed, archived)"),
    goal_type: Optional[str] = Query(None, description="Filter by goal type"),
    include_progress: bool = Query(True, description="Include current progress data")
):
    """
    Get all goals with optional filtering.
    """
    try:
        service = GoalsService()
        goals = await service.get_goals(status=status, goal_type=goal_type, include_progress=include_progress)
        
        return [goal.to_dict() for goal in goals]
        
    except Exception as e:
        logger.error(f"Error retrieving goals: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goals")


@router.get("/{goal_id}", response_model=Dict[str, Any])
async def get_goal(goal_id: int, include_progress: bool = Query(True)):
    """
    Get a specific goal by ID.
    """
    try:
        service = GoalsService()
        goal = await service.get_goal(goal_id, include_progress=include_progress)
        
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        return goal.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goal")


@router.post("/", response_model=Dict[str, Any], status_code=201)
async def create_goal(goal_data: Dict[str, Any]):
    """
    Create a new goal.
    
    Expected goal_data structure:
    {
        "goal_type": "steps",
        "target_value": 10000,
        "frequency": "daily",
        "description": "Walk 10,000 steps daily"
    }
    """
    try:
        # Validate required fields
        required_fields = ["goal_type", "target_value", "frequency"]
        for field in required_fields:
            if field not in goal_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Validate goal type
        if goal_data["goal_type"] not in GoalType.all():
            valid_types = ", ".join(GoalType.all())
            raise HTTPException(status_code=400, detail=f"Invalid goal_type. Valid types: {valid_types}")
        
        # Validate frequency
        if goal_data["frequency"] not in GoalFrequency.all():
            valid_frequencies = ", ".join(GoalFrequency.all())
            raise HTTPException(status_code=400, detail=f"Invalid frequency. Valid frequencies: {valid_frequencies}")
        
        # Validate target value
        if not isinstance(goal_data["target_value"], (int, float)) or goal_data["target_value"] <= 0:
            raise HTTPException(status_code=400, detail="target_value must be a positive number")
        
        service = GoalsService()
        goal = await service.create_goal(goal_data)
        
        return goal.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail="Failed to create goal")


@router.put("/{goal_id}", response_model=Dict[str, Any])
async def update_goal(goal_id: int, goal_data: Dict[str, Any]):
    """
    Update an existing goal.
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        existing_goal = await service.get_goal(goal_id)
        if not existing_goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Validate updates if provided
        if "goal_type" in goal_data and goal_data["goal_type"] not in GoalType.all():
            valid_types = ", ".join(GoalType.all())
            raise HTTPException(status_code=400, detail=f"Invalid goal_type. Valid types: {valid_types}")
        
        if "frequency" in goal_data and goal_data["frequency"] not in GoalFrequency.all():
            valid_frequencies = ", ".join(GoalFrequency.all())
            raise HTTPException(status_code=400, detail=f"Invalid frequency. Valid frequencies: {valid_frequencies}")
        
        if "target_value" in goal_data:
            if not isinstance(goal_data["target_value"], (int, float)) or goal_data["target_value"] <= 0:
                raise HTTPException(status_code=400, detail="target_value must be a positive number")
        
        if "status" in goal_data and goal_data["status"] not in [s.value for s in GoalStatus]:
            valid_statuses = ", ".join([s.value for s in GoalStatus])
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid statuses: {valid_statuses}")
        
        goal = await service.update_goal(goal_id, goal_data)
        
        return goal.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update goal")


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(goal_id: int):
    """
    Delete a goal and all associated data (streaks, achievements, etc.).
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        existing_goal = await service.get_goal(goal_id)
        if not existing_goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        success = await service.delete_goal(goal_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete goal")
        
        return JSONResponse(status_code=204, content=None)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete goal")


@router.get("/{goal_id}/streak", response_model=Dict[str, Any])
async def get_goal_streak(goal_id: int):
    """
    Get streak information for a specific goal.
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        streak = await service.get_streak(goal_id)
        
        if not streak:
            # Create initial streak record if it doesn't exist
            streak = await service.create_streak(goal_id)
        
        return streak.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving streak for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve streak")


@router.get("/{goal_id}/achievements", response_model=List[Dict[str, Any]])
async def get_goal_achievements(
    goal_id: int,
    limit: int = Query(50, description="Maximum number of achievements to return"),
    offset: int = Query(0, description="Number of achievements to skip")
):
    """
    Get achievement history for a specific goal.
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        achievements = await service.get_achievements(goal_id, limit=limit, offset=offset)
        
        return [achievement.to_dict() for achievement in achievements]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving achievements for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve achievements")


@router.post("/{goal_id}/achievements", response_model=Dict[str, Any], status_code=201)
async def record_goal_achievement(goal_id: int, achievement_data: Dict[str, Any]):
    """
    Record a goal achievement.
    
    Expected achievement_data structure:
    {
        "actual_value": 12500,
        "achieved_date": "2024-01-15",  # Optional, defaults to today
        "notes": "Exceeded goal by walking to work"  # Optional
    }
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Validate required fields
        if "actual_value" not in achievement_data:
            raise HTTPException(status_code=400, detail="Missing required field: actual_value")
        
        if not isinstance(achievement_data["actual_value"], (int, float)) or achievement_data["actual_value"] < 0:
            raise HTTPException(status_code=400, detail="actual_value must be a non-negative number")
        
        # Validate date if provided
        if "achieved_date" in achievement_data:
            try:
                datetime.fromisoformat(achievement_data["achieved_date"])
            except ValueError:
                raise HTTPException(status_code=400, detail="achieved_date must be in ISO format (YYYY-MM-DD)")
        
        achievement = await service.record_achievement(goal_id, achievement_data)
        
        return achievement.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording achievement for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record achievement")


@router.get("/{goal_id}/freeze-tokens", response_model=List[Dict[str, Any]])
async def get_freeze_tokens(goal_id: int):
    """
    Get available freeze tokens for a goal's streak.
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        tokens = await service.get_freeze_tokens(goal_id)
        
        return [token.to_dict() for token in tokens]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving freeze tokens for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve freeze tokens")


@router.post("/{goal_id}/freeze-tokens/use", response_model=Dict[str, Any])
async def use_freeze_token(goal_id: int, token_data: Dict[str, Any]):
    """
    Use a freeze token to preserve a streak.
    
    Expected token_data structure:
    {
        "token_id": 123,
        "used_date": "2024-01-15"  # Optional, defaults to today
    }
    """
    try:
        service = GoalsService()
        
        # Check if goal exists
        goal = await service.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Validate required fields
        if "token_id" not in token_data:
            raise HTTPException(status_code=400, detail="Missing required field: token_id")
        
        # Validate date if provided
        used_date = date.today()
        if "used_date" in token_data:
            try:
                used_date = datetime.fromisoformat(token_data["used_date"]).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="used_date must be in ISO format (YYYY-MM-DD)")
        
        success = await service.use_freeze_token(token_data["token_id"], used_date)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to use freeze token (may be already used or expired)")
        
        return {"message": "Freeze token used successfully", "used_date": used_date.isoformat()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using freeze token for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to use freeze token")


@router.get("/types", response_model=List[Dict[str, str]])
async def get_goal_types():
    """
    Get all available goal types with their display names and units.
    """
    try:
        return [
            {
                "value": goal_type.value,
                "display_name": goal_type.display_name(),
                "unit": goal_type.unit()
            }
            for goal_type in GoalType
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving goal types: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goal types")


@router.get("/frequencies", response_model=List[str])
async def get_goal_frequencies():
    """
    Get all available goal frequencies.
    """
    try:
        return GoalFrequency.all()
        
    except Exception as e:
        logger.error(f"Error retrieving goal frequencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve goal frequencies")


@router.get("/summary", response_model=Dict[str, Any])
async def get_goals_summary():
    """
    Get summary statistics for all goals.
    """
    try:
        service = GoalsService()
        summary = await service.get_goals_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating goals summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate goals summary")