"""
Job status and management API endpoints for Health Tracker.
Provides access to job status, history, and manual job execution.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..scheduler import get_scheduler

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    name: str
    description: str
    enabled: bool
    interval_minutes: int
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int
    failure_count: int
    last_result: Optional[Dict[str, Any]] = None


class JobHistoryResponse(BaseModel):
    """Response model for job execution history."""
    job_name: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    success: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class JobExecutionResponse(BaseModel):
    """Response model for manual job execution."""
    job_name: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    success: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SchedulerStatusResponse(BaseModel):
    """Response model for overall scheduler status."""
    running: bool
    total_jobs: int
    enabled_jobs: int
    disabled_jobs: int
    jobs_due_now: int
    next_job_due: Optional[str] = None


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """
    Get overall scheduler status and summary.
    """
    try:
        scheduler = get_scheduler()
        
        all_jobs = scheduler.get_all_jobs_status()
        enabled_jobs = sum(1 for job in all_jobs.values() if job['enabled'])
        disabled_jobs = len(all_jobs) - enabled_jobs
        
        # Find jobs due now and next due job
        jobs_due_now = 0
        next_due_time = None
        
        for job_status in all_jobs.values():
            if job_status['enabled'] and job_status['next_run']:
                next_run = datetime.fromisoformat(job_status['next_run'])
                
                if next_run <= datetime.now():
                    jobs_due_now += 1
                elif next_due_time is None or next_run < next_due_time:
                    next_due_time = next_run
        
        return SchedulerStatusResponse(
            running=scheduler.running,
            total_jobs=len(all_jobs),
            enabled_jobs=enabled_jobs,
            disabled_jobs=disabled_jobs,
            jobs_due_now=jobs_due_now,
            next_job_due=next_due_time.isoformat() if next_due_time else None
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs", response_model=Dict[str, JobStatusResponse])
async def get_all_jobs():
    """
    Get status for all registered jobs.
    """
    try:
        scheduler = get_scheduler()
        all_jobs = scheduler.get_all_jobs_status()
        
        response = {}
        for job_name, job_data in all_jobs.items():
            response[job_name] = JobStatusResponse(
                name=job_data['name'],
                description=job_data['description'],
                enabled=job_data['enabled'],
                interval_minutes=job_data['interval_minutes'],
                next_run=job_data['next_run'],
                last_run=job_data['last_run'],
                run_count=job_data['run_count'],
                failure_count=job_data['failure_count'],
                last_result=job_data['last_result']
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting all jobs status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs/{job_name}", response_model=JobStatusResponse)
async def get_job_status(
    job_name: str):
    """
    Get status for a specific job.
    """
    try:
        scheduler = get_scheduler()
        job_status = scheduler.get_job_status(job_name)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")
        
        return JobStatusResponse(
            name=job_status['name'],
            description=job_status['description'],
            enabled=job_status['enabled'],
            interval_minutes=job_status['interval_minutes'],
            next_run=job_status['next_run'],
            last_run=job_status['last_run'],
            run_count=job_status['run_count'],
            failure_count=job_status['failure_count'],
            last_result=job_status['last_result']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs/{job_name}/run", response_model=JobExecutionResponse)
async def run_job_now(
    job_name: str):
    """
    Manually trigger a job to run immediately.
    """
    try:
        scheduler = get_scheduler()
        
        # Check if job exists
        if not scheduler.get_job_status(job_name):
            raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")
        
        logger.info(f"Manual job execution requested: {job_name}")
        
        # Execute the job
        result = scheduler.run_job_now(job_name)
        
        if not result:
            raise HTTPException(status_code=500, detail="Job execution failed")
        
        return JobExecutionResponse(
            job_name=result.job_name,
            status=result.status.value,
            start_time=result.start_time.isoformat(),
            end_time=result.end_time.isoformat() if result.end_time else None,
            duration_seconds=result.duration_seconds,
            success=result.success,
            error_message=result.error_message,
            details=result.details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running job {job_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs/{job_name}/enable")
async def enable_job(
    job_name: str):
    """
    Enable a job.
    """
    try:
        scheduler = get_scheduler()
        
        if not scheduler.enable_job(job_name):
            raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")
        
        logger.info(f"Job enabled: {job_name}")
        
        return {"message": f"Job {job_name} enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling job {job_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs/{job_name}/disable")
async def disable_job(
    job_name: str):
    """
    Disable a job.
    """
    try:
        scheduler = get_scheduler()
        
        if not scheduler.disable_job(job_name):
            raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")
        
        logger.info(f"Job disabled: {job_name}")
        
        return {"message": f"Job {job_name} disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling job {job_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=List[JobHistoryResponse])
async def get_job_history(
    limit: Optional[int] = Query(50, description="Maximum number of history entries to return")):
    """
    Get job execution history.
    """
    try:
        scheduler = get_scheduler()
        history = scheduler.get_job_history(limit)
        
        return [
            JobHistoryResponse(
                job_name=entry['job_name'],
                status=entry['status'],
                start_time=entry['start_time'],
                end_time=entry['end_time'],
                duration_seconds=entry['duration_seconds'],
                success=entry['success'],
                error_message=entry['error_message'],
                details=entry['details']
            )
            for entry in history
        ]
        
    except Exception as e:
        logger.error(f"Error getting job history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history/{job_name}", response_model=List[JobHistoryResponse])
async def get_job_history_by_name(
    job_name: str,
    limit: Optional[int] = Query(20, description="Maximum number of history entries to return")):
    """
    Get execution history for a specific job.
    """
    try:
        scheduler = get_scheduler()
        
        # Check if job exists
        if not scheduler.get_job_status(job_name):
            raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")
        
        all_history = scheduler.get_job_history(limit * 2)  # Get more to filter
        job_history = [entry for entry in all_history if entry['job_name'] == job_name]
        
        # Apply limit after filtering
        if limit:
            job_history = job_history[:limit]
        
        return [
            JobHistoryResponse(
                job_name=entry['job_name'],
                status=entry['status'],
                start_time=entry['start_time'],
                end_time=entry['end_time'],
                duration_seconds=entry['duration_seconds'],
                success=entry['success'],
                error_message=entry['error_message'],
                details=entry['details']
            )
            for entry in job_history
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job history for {job_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/start")
async def start_scheduler():
    """
    Start the job scheduler if not already running.
    """
    try:
        scheduler = get_scheduler()
        
        if scheduler.running:
            return {"message": "Scheduler is already running"}
        
        scheduler.start()
        logger.info("Scheduler started via API")
        
        return {"message": "Scheduler started successfully"}
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop")
async def stop_scheduler():
    """
    Stop the job scheduler.
    """
    try:
        scheduler = get_scheduler()
        
        if not scheduler.running:
            return {"message": "Scheduler is not running"}
        
        scheduler.stop()
        logger.info("Scheduler stopped via API")
        
        return {"message": "Scheduler stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")