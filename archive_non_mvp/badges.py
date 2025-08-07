"""
Badges API - Health Tracker
REST endpoints for badge retrieval, progress tracking, and achievement management
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..services.badges_service import BadgesService

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/badges", tags=["badges"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_badges(
    earned_only: bool = Query(False, description="Only return earned badges"),
    category: Optional[str] = Query(None, description="Filter by category (steps, sleep, weight, etc.)")
):
    """
    Get all badges with their earned status.
    
    Query Parameters:
    - earned_only: If true, only return badges that have been earned
    - category: Filter badges by category
    """
    try:
        service = BadgesService()
        badges = await service.get_all_badges(earned_only=earned_only)
        
        # Filter by category if specified
        if category:
            badges = [b for b in badges if b.get('category') == category]
        
        return badges
        
    except Exception as e:
        logger.error(f"Error retrieving badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badges")


@router.get("/progress", response_model=Dict[str, Any])
async def get_badge_progress():
    """
    Get overall badge progress statistics.
    
    Returns:
    - Total badges available
    - Number of badges earned
    - Total points earned
    - Completion percentage
    - Progress by category
    - Recently earned badges
    """
    try:
        service = BadgesService()
        progress = await service.get_badge_progress()
        
        return progress
        
    except Exception as e:
        logger.error(f"Error retrieving badge progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badge progress")


@router.get("/next", response_model=List[Dict[str, Any]])
async def get_next_badges(
    limit: int = Query(3, description="Maximum number of badges to return", ge=1, le=10)
):
    """
    Get the next badges that are closest to being earned.
    
    Query Parameters:
    - limit: Maximum number of badges to return (1-10)
    """
    try:
        service = BadgesService()
        next_badges = await service.get_next_badges(limit=limit)
        
        return next_badges
        
    except Exception as e:
        logger.error(f"Error retrieving next badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve next badges")


@router.post("/evaluate", response_model=List[Dict[str, Any]])
async def evaluate_badges():
    """
    Evaluate all badges and automatically earn those that meet criteria.
    
    Returns:
    - List of newly earned badges
    """
    try:
        service = BadgesService()
        newly_earned = await service.evaluate_and_earn_badges()
        
        logger.info(f"Badge evaluation complete: {len(newly_earned)} new badges earned")
        
        return newly_earned
        
    except Exception as e:
        logger.error(f"Error evaluating badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate badges")


@router.get("/categories", response_model=List[Dict[str, str]])
async def get_badge_categories():
    """
    Get all available badge categories.
    """
    try:
        # Define available categories
        categories = [
            {"value": "steps", "display_name": "Steps", "icon": "🚶"},
            {"value": "sleep", "display_name": "Sleep", "icon": "😴"},
            {"value": "weight", "display_name": "Weight", "icon": "⚖️"},
            {"value": "heart_rate", "display_name": "Heart Rate", "icon": "❤️"},
            {"value": "hrv", "display_name": "HRV", "icon": "💗"},
            {"value": "overall", "display_name": "Overall", "icon": "⭐"}
        ]
        
        return categories
        
    except Exception as e:
        logger.error(f"Error retrieving badge categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badge categories")


@router.get("/tiers", response_model=Dict[str, Any])
async def get_badge_tiers():
    """
    Get information about badge tiers.
    """
    try:
        service = BadgesService()
        tiers = service.evaluator.badge_definitions.get('tiers', {})
        
        return tiers
        
    except Exception as e:
        logger.error(f"Error retrieving badge tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badge tiers")


@router.get("/{badge_id}", response_model=Dict[str, Any])
async def get_badge_details(badge_id: str):
    """
    Get detailed information about a specific badge.
    
    Path Parameters:
    - badge_id: The unique identifier of the badge
    """
    try:
        service = BadgesService()
        all_badges = await service.get_all_badges()
        
        # Find the specific badge
        badge = next((b for b in all_badges if b.get('id') == badge_id), None)
        
        if not badge:
            raise HTTPException(status_code=404, detail="Badge not found")
        
        # Add additional details if needed
        badge['tier_details'] = service.evaluator.badge_definitions['tiers'].get(
            badge.get('tier', 'bronze')
        )
        
        return badge
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving badge details for {badge_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badge details")


@router.get("/ui/display", response_model=Dict[str, Any])
async def get_badge_display_data():
    """
    Get badge data formatted for UI display.
    Includes earned badges, next badges to earn, and progress summary.
    """
    try:
        service = BadgesService()
        
        # Get all data needed for UI
        all_badges = await service.get_all_badges()
        progress = await service.get_badge_progress()
        next_badges = await service.get_next_badges(limit=3)
        
        # Format for UI display
        earned_badges = [b for b in all_badges if b['earned']]
        earned_badges.sort(key=lambda x: x.get('earned_at', ''), reverse=True)
        
        # Group by tier for display
        by_tier = {
            'bronze': [],
            'silver': [],
            'gold': [],
            'platinum': []
        }
        
        for badge in earned_badges:
            tier = badge.get('tier', 'bronze')
            if tier in by_tier:
                by_tier[tier].append(badge)
        
        return {
            'summary': {
                'total_earned': progress['earned_badges'],
                'total_available': progress['total_badges'],
                'total_points': progress['total_points'],
                'completion_percentage': progress['completion_percentage']
            },
            'earned_by_tier': by_tier,
            'recent_badges': progress['recent_badges'][:3],
            'next_to_earn': next_badges,
            'categories': progress['by_category']
        }
        
    except Exception as e:
        logger.error(f"Error getting badge display data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get badge display data")