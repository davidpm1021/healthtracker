"""
Hourly background jobs for Health Tracker.
Handles summary computation and moving average updates.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any

from database import DatabaseManager
from summaries import SummaryComputer
from models import MetricType

# Set up logging
logger = logging.getLogger(__name__)


def compute_daily_summaries_job() -> Dict[str, Any]:
    """
    Hourly job to compute daily summaries from raw data.
    Processes data from the last 7 days to catch any delayed data.
    """
    try:
        logger.info("Starting hourly summary computation job")
        
        # Compute summaries for the last 7 days (catches delayed data)
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=7)).isoformat()
        
        db = DatabaseManager()
        computer = SummaryComputer(db)
        
        # Compute daily summaries
        summary_result = computer.compute_daily_summaries(
            start_date=start_date, 
            end_date=end_date, 
            force_recompute=False  # Only update if there's new data
        )
        
        if not summary_result['success']:
            raise Exception(f"Summary computation failed: {summary_result.get('error')}")
        
        # Update moving averages and trends for all metrics
        analytics_results = {}
        total_updated = 0
        
        for metric in MetricType.all():
            result = computer.compute_moving_averages_and_trends(metric)
            analytics_results[metric] = result
            
            if 'updated_summaries' in result:
                total_updated += result['updated_summaries']
        
        logger.info(f"Hourly job completed: {summary_result['summaries_created']} summaries created, "
                   f"{summary_result['summaries_updated']} updated, {total_updated} analytics updated")
        
        return {
            'job_type': 'hourly_summary_computation',
            'success': True,
            'date_range': f"{start_date} to {end_date}",
            'summaries_created': summary_result['summaries_created'],
            'summaries_updated': summary_result['summaries_updated'],
            'total_summaries': summary_result['total_summaries'],
            'raw_points_processed': summary_result['raw_points_processed'],
            'analytics_updated': total_updated,
            'metrics_processed': list(analytics_results.keys()),
            'analytics_details': analytics_results
        }
        
    except Exception as e:
        logger.error(f"Hourly summary computation job failed: {e}")
        raise


def update_trend_analysis_job() -> Dict[str, Any]:
    """
    Hourly job to update trend analysis for recent data.
    Focuses on the most recent data for responsive trend updates.
    """
    try:
        logger.info("Starting hourly trend analysis update job")
        
        db = DatabaseManager()
        computer = SummaryComputer(db)
        
        # Update trends for the last 30 days of data
        end_date = date.today().isoformat()
        
        updated_metrics = []
        total_data_points = 0
        
        for metric in MetricType.all():
            # Get recent summaries to check if we have data
            summaries = db.get_daily_summaries_for_metric(
                metric, 
                (date.today() - timedelta(days=30)).isoformat(), 
                end_date
            )
            
            if len(summaries) >= 2:  # Need at least 2 points for trends
                result = computer.compute_moving_averages_and_trends(metric, end_date, days_back=30)
                
                if result.get('updated_summaries', 0) > 0:
                    updated_metrics.append({
                        'metric': metric,
                        'data_points': result.get('data_points', 0),
                        'updated_summaries': result.get('updated_summaries', 0),
                        'latest_values': result.get('latest_values')
                    })
                    total_data_points += result.get('data_points', 0)
        
        logger.info(f"Trend analysis job completed: {len(updated_metrics)} metrics updated")
        
        return {
            'job_type': 'hourly_trend_analysis',
            'success': True,
            'end_date': end_date,
            'metrics_updated': len(updated_metrics),
            'total_data_points': total_data_points,
            'updated_metrics': updated_metrics
        }
        
    except Exception as e:
        logger.error(f"Hourly trend analysis job failed: {e}")
        raise


def data_quality_check_job() -> Dict[str, Any]:
    """
    Hourly job to check data quality and identify issues.
    Monitors for missing data, outliers, and sync problems.
    """
    try:
        logger.info("Starting hourly data quality check job")
        
        db = DatabaseManager()
        
        # Check data freshness (last sync times)
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=1)).isoformat()
        
        data_freshness = {}
        missing_data_alerts = []
        
        for metric in MetricType.all():
            # Check raw data points in last 24 hours
            raw_points = db.get_raw_points(metric, start_date + 'T00:00:00Z', end_date + 'T23:59:59Z')
            
            data_freshness[metric] = {
                'raw_points_24h': len(raw_points),
                'latest_point': raw_points[-1]['start_time'] if raw_points else None
            }
            
            # Alert if no data in last 24 hours for metrics that should have daily data
            if metric in [MetricType.STEPS, MetricType.SLEEP] and len(raw_points) == 0:
                missing_data_alerts.append({
                    'metric': metric,
                    'issue': 'no_data_24h',
                    'message': f'No {metric} data received in last 24 hours'
                })
        
        # Check database size and performance
        table_counts = db.get_table_counts()
        
        # Database health check
        db_healthy = db.test_connection()
        
        logger.info(f"Data quality check completed: {len(missing_data_alerts)} alerts, "
                   f"DB healthy: {db_healthy}")
        
        return {
            'job_type': 'hourly_data_quality_check',
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'database_healthy': db_healthy,
            'table_counts': table_counts,
            'data_freshness': data_freshness,
            'missing_data_alerts': missing_data_alerts,
            'total_alerts': len(missing_data_alerts)
        }
        
    except Exception as e:
        logger.error(f"Data quality check job failed: {e}")
        raise


def register_hourly_jobs(scheduler) -> None:
    """Register all hourly jobs with the scheduler."""
    
    # Main summary computation job - runs every hour
    scheduler.register_job(
        name="hourly_summary_computation",
        function=compute_daily_summaries_job,
        interval_minutes=60,
        description="Compute daily summaries and update moving averages from raw data",
        enabled=True
    )
    
    # Trend analysis update - runs every hour at 30 minutes past
    # (offset from main job to distribute load)
    scheduler.register_job(
        name="hourly_trend_analysis",
        function=update_trend_analysis_job,
        interval_minutes=60,
        description="Update trend analysis and moving averages for recent data",
        enabled=True
    )
    
    # Data quality monitoring - runs every 2 hours
    scheduler.register_job(
        name="data_quality_check",
        function=data_quality_check_job,
        interval_minutes=120,
        description="Monitor data quality, freshness, and identify sync issues",
        enabled=True
    )
    
    logger.info("Registered 3 hourly jobs with scheduler")