"""
Background jobs for Health Tracker.
Handles scheduled tasks like summary updates and database maintenance.
"""
from .hourly import register_hourly_jobs
from .nightly import register_nightly_jobs

__all__ = ['register_hourly_jobs', 'register_nightly_jobs']


def register_all_jobs():
    """Register all background jobs with the scheduler."""
    from scheduler import get_scheduler
    
    scheduler = get_scheduler()
    
    # Register hourly jobs
    register_hourly_jobs(scheduler)
    
    # Register nightly jobs
    register_nightly_jobs(scheduler)
    
    return scheduler