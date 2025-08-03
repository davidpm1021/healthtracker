"""
Summary API endpoints for Health Tracker.
Provides access to daily summaries, moving averages, and trend analysis.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import logging

from database import DatabaseManager
from models import MetricType
from summaries import SummaryComputer, compute_daily_summaries, update_all_analytics
from trends import analyze_metric_trends
from auth import require_auth

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class SummaryResponse(BaseModel):
    """Response model for daily summaries."""
    date: str
    metric: str
    value: float
    unit: str
    avg_7day: Optional[float] = None
    avg_30day: Optional[float] = None
    trend_slope: Optional[float] = None
    created_at: str
    updated_at: str


class MetricSummariesResponse(BaseModel):
    """Response model for metric summaries."""
    metric: str
    start_date: str
    end_date: str
    data_points: int
    summaries: List[SummaryResponse]


class TrendAnalysisResponse(BaseModel):
    """Response model for trend analysis."""
    metric: str
    data_points: int
    date_range: Optional[tuple]
    current_value: Optional[float]
    trend: Dict[str, Any]
    moving_averages: Dict[str, Any]
    statistics: Dict[str, Any]
    patterns: Dict[str, Any]


class ComputationResponse(BaseModel):
    """Response model for summary computation operations."""
    success: bool
    summaries_created: int
    summaries_updated: int
    total_summaries: int
    date_range: tuple
    raw_points_processed: int
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/summaries/{metric}", response_model=MetricSummariesResponse)
async def get_metric_summaries(
    metric: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(100, description="Maximum number of summaries to return"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Get daily summaries for a specific metric within a date range.
    """
    try:
        # Validate metric
        if metric not in MetricType.all():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {MetricType.all()}"
            )
        
        # Set default date range if not provided
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        # Validate dates
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
        
        # Get summaries from database
        db = DatabaseManager()
        summaries = db.get_daily_summaries_for_metric(metric, start_date, end_date)
        
        # Apply limit
        if limit and len(summaries) > limit:
            summaries = summaries[-limit:]  # Get most recent
        
        # Convert to response format
        summary_responses = [
            SummaryResponse(
                date=summary['date'],
                metric=summary['metric'],
                value=summary['value'],
                unit=summary['unit'],
                avg_7day=summary.get('avg_7day'),
                avg_30day=summary.get('avg_30day'),
                trend_slope=summary.get('trend_slope'),
                created_at=summary['created_at'],
                updated_at=summary['updated_at']
            )
            for summary in summaries
        ]
        
        return MetricSummariesResponse(
            metric=metric,
            start_date=start_date,
            end_date=end_date,
            data_points=len(summary_responses),
            summaries=summary_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving summaries for {metric}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summaries", response_model=Dict[str, MetricSummariesResponse])
async def get_all_summaries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(30, description="Maximum number of summaries per metric"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Get daily summaries for all metrics within a date range.
    """
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        # Validate dates
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
        
        db = DatabaseManager()
        all_summaries = {}
        
        for metric in MetricType.all():
            summaries = db.get_daily_summaries_for_metric(metric, start_date, end_date)
            
            # Apply limit
            if limit and len(summaries) > limit:
                summaries = summaries[-limit:]
            
            summary_responses = [
                SummaryResponse(
                    date=summary['date'],
                    metric=summary['metric'],
                    value=summary['value'],
                    unit=summary['unit'],
                    avg_7day=summary.get('avg_7day'),
                    avg_30day=summary.get('avg_30day'),
                    trend_slope=summary.get('trend_slope'),
                    created_at=summary['created_at'],
                    updated_at=summary['updated_at']
                )
                for summary in summaries
            ]
            
            all_summaries[metric] = MetricSummariesResponse(
                metric=metric,
                start_date=start_date,
                end_date=end_date,
                data_points=len(summary_responses),
                summaries=summary_responses
            )
        
        return all_summaries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving all summaries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trends/{metric}", response_model=TrendAnalysisResponse)
async def get_metric_trends(
    metric: str,
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Get trend analysis for a specific metric.
    """
    try:
        # Validate metric
        if metric not in MetricType.all():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {MetricType.all()}"
            )
        
        # Validate days parameter
        if days <= 0 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
        
        # Get summaries for analysis
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days)).date().isoformat()
        
        db = DatabaseManager()
        summaries = db.get_daily_summaries_for_metric(metric, start_date, end_date)
        
        if not summaries:
            raise HTTPException(
                status_code=404,
                detail=f"No summary data found for {metric} in the specified period"
            )
        
        # Perform trend analysis
        analysis = analyze_metric_trends(summaries, metric, days)
        
        return TrendAnalysisResponse(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing trends for {metric}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/compute", response_model=ComputationResponse)
async def compute_summaries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    force_recompute: bool = Query(False, description="Force recomputation of existing summaries"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Compute daily summaries from raw data.
    """
    try:
        # Validate dates if provided
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="start_date must be in YYYY-MM-DD format")
        
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="end_date must be in YYYY-MM-DD format")
        
        # Compute summaries
        result = compute_daily_summaries(start_date, end_date, force_recompute)
        
        if result['success']:
            return ComputationResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Computation failed'))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing summaries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/update-analytics", response_model=Dict[str, Any])
async def update_analytics(
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Update moving averages and trends for all metrics.
    """
    try:
        # Validate date if provided
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="end_date must be in YYYY-MM-DD format")
        
        # Update analytics
        result = update_all_analytics(end_date)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_summary_statistics(
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    auth_context: Dict[str, Any] = Depends(require_auth)
):
    """
    Get summary statistics for all metrics.
    """
    try:
        # Validate days parameter
        if days <= 0 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
        
        db = DatabaseManager()
        computer = SummaryComputer(db)
        stats = computer.get_summary_statistics(days)
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")