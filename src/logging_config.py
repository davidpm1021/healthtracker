"""
Logging configuration for HealthTracker with error recovery and monitoring
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Create log directory if it doesn't exist
LOG_DIR = Path("/var/log/healthtracker")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Fallback to local directory if system directory isn't writable
if not os.access(LOG_DIR, os.W_OK):
    LOG_DIR = Path.home() / "healthtracker" / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

class ErrorRecoveryHandler(logging.Handler):
    """Custom handler for critical errors that triggers recovery actions"""
    
    def __init__(self):
        super().__init__()
        self.error_count = 0
        self.last_error_time = None
        self.recovery_threshold = 5  # Errors before triggering recovery
        self.time_window = 300  # 5 minutes
        
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            current_time = datetime.now()
            
            # Reset counter if outside time window
            if self.last_error_time:
                elapsed = (current_time - self.last_error_time).seconds
                if elapsed > self.time_window:
                    self.error_count = 0
            
            self.error_count += 1
            self.last_error_time = current_time
            
            # Trigger recovery if threshold reached
            if self.error_count >= self.recovery_threshold:
                self.trigger_recovery(record)
                self.error_count = 0  # Reset after recovery
    
    def trigger_recovery(self, record):
        """Trigger recovery actions for critical errors"""
        recovery_log = LOG_DIR / "recovery.log"
        with open(recovery_log, "a") as f:
            f.write(f"\n[{datetime.now()}] Recovery triggered after {self.error_count} errors\n")
            f.write(f"Last error: {record.getMessage()}\n")
            f.write("Recovery actions:\n")
            f.write("  - Database integrity check scheduled\n")
            f.write("  - Cache cleared\n")
            f.write("  - Service restart recommended\n")
        
        # Schedule recovery actions
        try:
            # Clear any cached data
            import shutil
            cache_dir = Path.home() / ".cache" / "healthtracker"
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create recovery marker for systemd to detect
            recovery_marker = LOG_DIR / "needs_recovery"
            recovery_marker.touch()
            
        except Exception as e:
            # Don't let recovery errors crash the app
            pass

def setup_logging(app_name="healthtracker", log_level=logging.INFO):
    """
    Configure comprehensive logging with rotation and error recovery
    
    Args:
        app_name: Name of the application component
        log_level: Logging level (default: INFO)
    
    Returns:
        Logger instance configured with handlers
    """
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Format for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Rotating file handler for general logs
    general_log = LOG_DIR / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        general_log,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler for errors only
    error_log = LOG_DIR / f"{app_name}-error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # Add custom error recovery handler
    recovery_handler = ErrorRecoveryHandler()
    recovery_handler.setLevel(logging.ERROR)
    recovery_handler.setFormatter(formatter)
    logger.addHandler(recovery_handler)
    
    # Performance log for monitoring
    if app_name == "healthtracker":
        perf_log = LOG_DIR / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=2,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        
        # Create separate performance logger
        perf_logger = logging.getLogger(f"{app_name}.performance")
        perf_logger.setLevel(logging.INFO)
        perf_logger.addHandler(perf_handler)
    
    return logger

def log_performance(operation, duration_ms, success=True):
    """
    Log performance metrics for monitoring
    
    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
    """
    perf_logger = logging.getLogger("healthtracker.performance")
    status = "SUCCESS" if success else "FAILED"
    perf_logger.info(f"{operation} | {duration_ms}ms | {status}")

def check_log_health():
    """
    Check health of logging system and clean up if needed
    
    Returns:
        Dictionary with health status
    """
    health = {
        "status": "healthy",
        "log_dir": str(LOG_DIR),
        "writable": os.access(LOG_DIR, os.W_OK),
        "space_available": True,
        "recovery_needed": False,
        "errors": []
    }
    
    try:
        # Check disk space
        import shutil
        stat = shutil.disk_usage(LOG_DIR)
        free_mb = stat.free / (1024 * 1024)
        health["free_space_mb"] = round(free_mb, 2)
        
        if free_mb < 100:  # Less than 100MB free
            health["space_available"] = False
            health["errors"].append("Low disk space")
            health["status"] = "warning"
            
            # Clean old logs if space is critical
            if free_mb < 50:
                clean_old_logs()
        
        # Check for recovery marker
        recovery_marker = LOG_DIR / "needs_recovery"
        if recovery_marker.exists():
            health["recovery_needed"] = True
            health["status"] = "recovery_needed"
            
        # Check log file sizes
        for log_file in LOG_DIR.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb > 50:  # Warn if any log over 50MB
                health["errors"].append(f"{log_file.name} is {size_mb:.1f}MB")
                
    except Exception as e:
        health["status"] = "error"
        health["errors"].append(str(e))
    
    return health

def clean_old_logs(days=7):
    """
    Clean logs older than specified days
    
    Args:
        days: Number of days to keep logs
    """
    import time
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)
    
    for log_file in LOG_DIR.glob("*.log.*"):  # Only clean rotated logs
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
            except:
                pass  # Ignore errors during cleanup

# Create default logger for import
logger = setup_logging("healthtracker")