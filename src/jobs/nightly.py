"""
Nightly background jobs for Health Tracker.
Handles database maintenance, backups, and cleanup operations.
"""
import os
import logging
import shutil
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any

from database import DatabaseManager

# Set up logging
logger = logging.getLogger(__name__)


def database_maintenance_job() -> Dict[str, Any]:
    """
    Nightly job to perform database maintenance operations.
    Includes VACUUM, ANALYZE, and integrity checks.
    """
    try:
        logger.info("Starting nightly database maintenance job")
        
        db = DatabaseManager()
        maintenance_results = {}
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get database size before maintenance
            db_path = Path(db.db_path)
            size_before = db_path.stat().st_size if db_path.exists() else 0
            
            # Run VACUUM to reclaim space
            logger.info("Running database VACUUM operation")
            vacuum_start = datetime.now()
            cursor.execute("VACUUM")
            vacuum_duration = (datetime.now() - vacuum_start).total_seconds()
            
            # Run ANALYZE to update query planner statistics
            logger.info("Running database ANALYZE operation")
            analyze_start = datetime.now()
            cursor.execute("ANALYZE")
            analyze_duration = (datetime.now() - analyze_start).total_seconds()
            
            # Check database integrity
            logger.info("Running database integrity check")
            integrity_start = datetime.now()
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            integrity_duration = (datetime.now() - integrity_start).total_seconds()
            
            # Get database size after maintenance
            size_after = db_path.stat().st_size if db_path.exists() else 0
            space_reclaimed = size_before - size_after
            
            # Get table statistics
            table_counts = db.get_table_counts()
            
            maintenance_results = {
                'vacuum_duration_seconds': round(vacuum_duration, 2),
                'analyze_duration_seconds': round(analyze_duration, 2),
                'integrity_check_duration_seconds': round(integrity_duration, 2),
                'integrity_result': integrity_result,
                'database_size_before_bytes': size_before,
                'database_size_after_bytes': size_after,
                'space_reclaimed_bytes': space_reclaimed,
                'table_counts': table_counts
            }
        
        logger.info(f"Database maintenance completed: "
                   f"reclaimed {space_reclaimed} bytes, integrity: {integrity_result}")
        
        return {
            'job_type': 'nightly_database_maintenance',
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'maintenance_results': maintenance_results
        }
        
    except Exception as e:
        logger.error(f"Database maintenance job failed: {e}")
        raise


def create_backup_job() -> Dict[str, Any]:
    """
    Nightly job to create timestamped database backups.
    Maintains weekly rolling backups with retention policy.
    """
    try:
        logger.info("Starting nightly backup creation job")
        
        db = DatabaseManager()
        
        # Create backup directory if it doesn't exist
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Create timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"healthtracker_backup_{timestamp}.db"
        backup_path = backup_dir / backup_filename
        
        # Create backup using SQLite backup API
        db_path = Path(db.db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Source database not found: {db_path}")
        
        # Perform backup
        backup_start = datetime.now()
        with sqlite3.connect(str(db_path)) as source_conn:
            with sqlite3.connect(str(backup_path)) as backup_conn:
                source_conn.backup(backup_conn)
        
        backup_duration = (datetime.now() - backup_start).total_seconds()
        
        # Get backup file size
        backup_size = backup_path.stat().st_size
        
        # Clean up old backups (keep last 7 daily backups)
        cleanup_results = _cleanup_old_backups(backup_dir, keep_days=7)
        
        logger.info(f"Backup created: {backup_filename} ({backup_size} bytes) "
                   f"in {backup_duration:.2f}s")
        
        return {
            'job_type': 'nightly_backup_creation',
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'backup_filename': backup_filename,
            'backup_size_bytes': backup_size,
            'backup_duration_seconds': round(backup_duration, 2),
            'cleanup_results': cleanup_results
        }
        
    except Exception as e:
        logger.error(f"Backup creation job failed: {e}")
        raise


def data_cleanup_job() -> Dict[str, Any]:
    """
    Nightly job to clean up old data and optimize storage.
    Removes very old raw data while preserving summaries.
    """
    try:
        logger.info("Starting nightly data cleanup job")
        
        db = DatabaseManager()
        cleanup_results = {}
        
        # Clean up raw data older than 90 days (keep summaries)
        cutoff_date = (date.today() - timedelta(days=90)).isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count old raw points before deletion
            cursor.execute("""
                SELECT COUNT(*) FROM raw_points 
                WHERE start_time < ?
            """, (cutoff_date + 'T00:00:00Z',))
            old_raw_points_count = cursor.fetchone()[0]
            
            # Delete old raw points
            if old_raw_points_count > 0:
                cursor.execute("""
                    DELETE FROM raw_points 
                    WHERE start_time < ?
                """, (cutoff_date + 'T00:00:00Z',))
                
                deleted_raw_points = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_raw_points} raw data points older than {cutoff_date}")
            else:
                deleted_raw_points = 0
                logger.info("No old raw data points to delete")
            
            # Clean up old sync logs (keep last 30 days)
            sync_cutoff_date = (date.today() - timedelta(days=30)).isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM sync_log 
                WHERE created_at < ?
            """, (sync_cutoff_date + 'T00:00:00Z',))
            old_sync_logs_count = cursor.fetchone()[0]
            
            if old_sync_logs_count > 0:
                cursor.execute("""
                    DELETE FROM sync_log 
                    WHERE created_at < ?
                """, (sync_cutoff_date + 'T00:00:00Z',))
                
                deleted_sync_logs = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_sync_logs} sync log entries older than {sync_cutoff_date}")
            else:
                deleted_sync_logs = 0
                logger.info("No old sync log entries to delete")
            
            # Get final table counts
            final_counts = db.get_table_counts()
            
            cleanup_results = {
                'raw_points_deleted': deleted_raw_points,
                'sync_logs_deleted': deleted_sync_logs,
                'cutoff_date': cutoff_date,
                'sync_cutoff_date': sync_cutoff_date,
                'final_table_counts': final_counts
            }
        
        logger.info(f"Data cleanup completed: {deleted_raw_points} raw points, "
                   f"{deleted_sync_logs} sync logs deleted")
        
        return {
            'job_type': 'nightly_data_cleanup',
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'cleanup_results': cleanup_results
        }
        
    except Exception as e:
        logger.error(f"Data cleanup job failed: {e}")
        raise


def system_health_report_job() -> Dict[str, Any]:
    """
    Nightly job to generate system health report.
    Provides overview of system status and performance.
    """
    try:
        logger.info("Starting nightly system health report job")
        
        db = DatabaseManager()
        
        # Get system statistics
        table_counts = db.get_table_counts()
        db_healthy = db.test_connection()
        
        # Check recent data activity
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        recent_activity = {}
        for table in ['raw_points', 'daily_summaries', 'manual_entries']:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                if table == 'raw_points':
                    cursor.execute("""
                        SELECT COUNT(*) FROM raw_points 
                        WHERE start_time >= ? AND start_time < ?
                    """, (yesterday + 'T00:00:00Z', today + 'T00:00:00Z'))
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {table} 
                        WHERE updated_at >= ? AND updated_at < ?
                    """, (yesterday + 'T00:00:00', today + 'T00:00:00'))
                
                recent_activity[table] = cursor.fetchone()[0]
        
        # Database file size
        db_path = Path(db.db_path)
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        # Check backup status
        backup_dir = Path("backups")
        backup_info = None
        if backup_dir.exists():
            backup_files = list(backup_dir.glob("healthtracker_backup_*.db"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                backup_info = {
                    'latest_backup': latest_backup.name,
                    'backup_age_hours': (datetime.now().timestamp() - latest_backup.stat().st_mtime) / 3600,
                    'backup_size_bytes': latest_backup.stat().st_size,
                    'total_backups': len(backup_files)
                }
        
        health_report = {
            'database_healthy': db_healthy,
            'database_size_bytes': db_size,
            'table_counts': table_counts,
            'recent_activity_24h': recent_activity,
            'backup_status': backup_info,
            'report_date': today
        }
        
        logger.info(f"System health report generated: DB size {db_size} bytes, "
                   f"healthy: {db_healthy}")
        
        return {
            'job_type': 'nightly_system_health_report',
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'health_report': health_report
        }
        
    except Exception as e:
        logger.error(f"System health report job failed: {e}")
        raise


def _cleanup_old_backups(backup_dir: Path, keep_days: int = 7) -> Dict[str, Any]:
    """Clean up backup files older than specified days."""
    try:
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
        
        backup_files = list(backup_dir.glob("healthtracker_backup_*.db"))
        old_files = [f for f in backup_files if f.stat().st_mtime < cutoff_time]
        
        deleted_count = 0
        deleted_size = 0
        
        for old_file in old_files:
            file_size = old_file.stat().st_size
            old_file.unlink()
            deleted_count += 1
            deleted_size += file_size
            logger.info(f"Deleted old backup: {old_file.name}")
        
        return {
            'deleted_files': deleted_count,
            'deleted_size_bytes': deleted_size,
            'remaining_backups': len(backup_files) - deleted_count,
            'cutoff_days': keep_days
        }
        
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        return {
            'deleted_files': 0,
            'deleted_size_bytes': 0,
            'error': str(e)
        }


def register_nightly_jobs(scheduler) -> None:
    """Register all nightly jobs with the scheduler."""
    
    # Database maintenance - runs daily at 2:00 AM equivalent (every 24 hours)
    scheduler.register_job(
        name="nightly_database_maintenance",
        function=database_maintenance_job,
        interval_minutes=24 * 60,  # 24 hours
        description="Perform database VACUUM, ANALYZE, and integrity checks",
        enabled=True
    )
    
    # Backup creation - runs daily at 2:30 AM equivalent
    scheduler.register_job(
        name="nightly_backup_creation",
        function=create_backup_job,
        interval_minutes=24 * 60,  # 24 hours
        description="Create timestamped database backups with retention policy",
        enabled=True
    )
    
    # Data cleanup - runs daily at 3:00 AM equivalent
    scheduler.register_job(
        name="nightly_data_cleanup",
        function=data_cleanup_job,
        interval_minutes=24 * 60,  # 24 hours
        description="Clean up old raw data and sync logs to optimize storage",
        enabled=True
    )
    
    # System health report - runs daily at 3:30 AM equivalent
    scheduler.register_job(
        name="nightly_system_health_report",
        function=system_health_report_job,
        interval_minutes=24 * 60,  # 24 hours
        description="Generate comprehensive system health and status report",
        enabled=True
    )
    
    logger.info("Registered 4 nightly jobs with scheduler")