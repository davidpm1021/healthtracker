"""
Background job scheduler for Health Tracker.
Manages hourly and nightly jobs for data processing and maintenance.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
import threading
import time
import traceback
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status constants."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class JobResult:
    """Result of a job execution."""
    job_name: str
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def complete_success(self, details: Dict[str, Any] = None):
        """Mark job as successfully completed."""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = JobStatus.SUCCESS
        self.success = True
        if details:
            self.details.update(details)

    def complete_failure(self, error: str, details: Dict[str, Any] = None):
        """Mark job as failed."""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = JobStatus.FAILED
        self.success = False
        self.error_message = error
        if details:
            self.details.update(details)


@dataclass
class JobDefinition:
    """Definition of a scheduled job."""
    name: str
    function: Callable[[], Dict[str, Any]]
    interval_minutes: int
    description: str = ""
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[JobResult] = None
    run_count: int = 0
    failure_count: int = 0

    def __post_init__(self):
        """Initialize next run time if not set."""
        if self.next_run is None and self.enabled:
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)

    def is_due(self) -> bool:
        """Check if job is due to run."""
        if not self.enabled or not self.next_run:
            return False
        return datetime.now() >= self.next_run

    def schedule_next_run(self):
        """Schedule the next run based on interval."""
        if self.enabled:
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
        else:
            self.next_run = None

    def execute(self) -> JobResult:
        """Execute the job and return result."""
        result = JobResult(
            job_name=self.name,
            status=JobStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self.last_run = result.start_time
        self.run_count += 1

        try:
            logger.info(f"Starting job: {self.name}")
            job_details = self.function()
            result.complete_success(job_details)
            logger.info(f"Job completed successfully: {self.name} (took {result.duration_seconds:.2f}s)")
            
        except Exception as e:
            error_msg = f"Job failed: {self.name} - {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            result.complete_failure(error_msg)
            self.failure_count += 1

        self.last_result = result
        self.schedule_next_run()
        return result


class JobScheduler:
    """Background job scheduler with configurable intervals."""

    def __init__(self):
        """Initialize job scheduler."""
        self.jobs: Dict[str, JobDefinition] = {}
        self.job_history: List[JobResult] = []
        self.max_history_size = 100
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def register_job(
        self,
        name: str,
        function: Callable[[], Dict[str, Any]],
        interval_minutes: int,
        description: str = "",
        enabled: bool = True
    ) -> None:
        """
        Register a new job with the scheduler.
        
        Args:
            name: Unique job name
            function: Function to execute (should return dict with job details)
            interval_minutes: How often to run the job
            description: Human-readable description
            enabled: Whether job is enabled
        """
        if name in self.jobs:
            logger.warning(f"Job {name} already registered, replacing")
        
        job = JobDefinition(
            name=name,
            function=function,
            interval_minutes=interval_minutes,
            description=description,
            enabled=enabled
        )
        
        self.jobs[name] = job
        logger.info(f"Registered job: {name} (interval: {interval_minutes}m, enabled: {enabled})")

    def unregister_job(self, name: str) -> bool:
        """Remove a job from the scheduler."""
        if name in self.jobs:
            del self.jobs[name]
            logger.info(f"Unregistered job: {name}")
            return True
        return False

    def enable_job(self, name: str) -> bool:
        """Enable a job."""
        if name in self.jobs:
            self.jobs[name].enabled = True
            self.jobs[name].schedule_next_run()
            logger.info(f"Enabled job: {name}")
            return True
        return False

    def disable_job(self, name: str) -> bool:
        """Disable a job."""
        if name in self.jobs:
            self.jobs[name].enabled = False
            self.jobs[name].next_run = None
            logger.info(f"Disabled job: {name}")
            return True
        return False

    def run_job_now(self, name: str) -> Optional[JobResult]:
        """Manually trigger a job to run immediately."""
        if name not in self.jobs:
            logger.error(f"Job not found: {name}")
            return None

        job = self.jobs[name]
        logger.info(f"Manually triggering job: {name}")
        result = job.execute()
        self._add_to_history(result)
        return result

    def get_job_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific job."""
        if name not in self.jobs:
            return None

        job = self.jobs[name]
        return {
            'name': job.name,
            'description': job.description,
            'enabled': job.enabled,
            'interval_minutes': job.interval_minutes,
            'next_run': job.next_run.isoformat() if job.next_run else None,
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'run_count': job.run_count,
            'failure_count': job.failure_count,
            'last_result': {
                'status': job.last_result.status.value if job.last_result else None,
                'success': job.last_result.success if job.last_result else None,
                'duration_seconds': job.last_result.duration_seconds if job.last_result else None,
                'error_message': job.last_result.error_message if job.last_result else None,
                'details': job.last_result.details if job.last_result else {}
            } if job.last_result else None
        }

    def get_all_jobs_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all registered jobs."""
        return {name: self.get_job_status(name) for name in self.jobs.keys()}

    def get_job_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent job execution history."""
        recent_history = self.job_history[-limit:] if limit else self.job_history
        return [
            {
                'job_name': result.job_name,
                'status': result.status.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'duration_seconds': result.duration_seconds,
                'success': result.success,
                'error_message': result.error_message,
                'details': result.details
            }
            for result in reversed(recent_history)
        ]

    def start(self) -> None:
        """Start the job scheduler in a background thread."""
        if self.running:
            logger.warning("Job scheduler is already running")
            return

        logger.info("Starting job scheduler")
        self.running = True
        self._stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

    def stop(self) -> None:
        """Stop the job scheduler."""
        if not self.running:
            logger.warning("Job scheduler is not running")
            return

        logger.info("Stopping job scheduler")
        self.running = False
        self._stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
            if self.scheduler_thread.is_alive():
                logger.warning("Job scheduler thread did not stop gracefully")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for due jobs."""
        logger.info("Job scheduler loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                # Check all jobs for due execution
                for job in self.jobs.values():
                    if job.is_due():
                        logger.info(f"Job is due: {job.name}")
                        result = job.execute()
                        self._add_to_history(result)

                # Sleep for 30 seconds before next check
                if self._stop_event.wait(timeout=30):
                    break

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                logger.error(traceback.format_exc())
                # Continue running even if there's an error
                time.sleep(60)  # Wait longer after an error

        logger.info("Job scheduler loop stopped")

    def _add_to_history(self, result: JobResult) -> None:
        """Add job result to history with size limit."""
        self.job_history.append(result)
        
        # Trim history if it exceeds max size
        if len(self.job_history) > self.max_history_size:
            self.job_history = self.job_history[-self.max_history_size:]


# Global scheduler instance
_scheduler_instance: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobScheduler()
    return _scheduler_instance


def initialize_scheduler() -> JobScheduler:
    """Initialize and start the global scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler


def shutdown_scheduler() -> None:
    """Shutdown the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance and _scheduler_instance.running:
        _scheduler_instance.stop()
        _scheduler_instance = None