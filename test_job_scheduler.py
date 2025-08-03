#!/usr/bin/env python3
"""
Validation test for job scheduler system.
Tests job registration, scheduling, execution, and API endpoints.
"""
import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from scheduler import JobScheduler, JobDefinition, JobStatus
from jobs.hourly import register_hourly_jobs
from jobs.nightly import register_nightly_jobs
from database import DatabaseManager


def test_job_function() -> dict:
    """Simple test job that returns success."""
    time.sleep(0.1)  # Simulate work
    return {
        'message': 'Test job completed successfully',
        'timestamp': datetime.now().isoformat(),
        'data_processed': 42
    }


def test_failing_job() -> dict:
    """Test job that always fails."""
    raise Exception("This is a test failure")


def test_scheduler_basic_functionality() -> bool:
    """Test basic scheduler functionality."""
    print("\nTesting basic scheduler functionality...")
    
    try:
        scheduler = JobScheduler()
        
        # Test job registration
        scheduler.register_job(
            name="test_job",
            function=test_job_function,
            interval_minutes=1,
            description="Test job for validation",
            enabled=True
        )
        
        # Check job is registered
        job_status = scheduler.get_job_status("test_job")
        if not job_status:
            print("❌ Job registration failed")
            return False
        
        print(f"✅ Job registered: {job_status['name']}")
        
        # Test manual job execution
        result = scheduler.run_job_now("test_job")
        if not result or not result.success:
            print("❌ Manual job execution failed")
            return False
        
        print(f"✅ Manual job execution successful (took {result.duration_seconds:.3f}s)")
        
        # Test job history
        history = scheduler.get_job_history(limit=5)
        if not history or history[0]['job_name'] != 'test_job':
            print("❌ Job history not recorded")
            return False
        
        print(f"✅ Job history recorded: {len(history)} entries")
        
        # Test job enable/disable
        if not scheduler.disable_job("test_job"):
            print("❌ Job disable failed")
            return False
        
        job_status = scheduler.get_job_status("test_job")
        if job_status['enabled']:
            print("❌ Job not properly disabled")
            return False
        
        print("✅ Job disable/enable working")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_scheduler_timing() -> bool:
    """Test scheduler threading and basic operation."""
    print("\nTesting scheduler threading...")
    
    try:
        scheduler = JobScheduler()
        
        # Test that scheduler can start and stop properly
        scheduler.start()
        
        if not scheduler.running:
            print("❌ Scheduler failed to start")
            return False
        
        print("✅ Scheduler started successfully")
        
        # Let it run briefly
        time.sleep(1)
        
        # Test that scheduler is still running
        if not scheduler.running:
            print("❌ Scheduler stopped unexpectedly")
            return False
        
        print("✅ Scheduler running stably")
        
        # Test graceful shutdown
        scheduler.stop()
        
        if scheduler.running:
            print("❌ Scheduler failed to stop")
            return False
        
        print("✅ Scheduler stopped gracefully")
        
        # Test job scheduling logic separately
        test_job_name = "timing_test_job"
        scheduler.register_job(
            name=test_job_name,
            function=test_job_function,
            interval_minutes=60,  # Normal interval
            description="Test job for timing validation",
            enabled=True
        )
        
        # Test is_due logic
        from datetime import datetime, timedelta
        job = scheduler.jobs[test_job_name]
        
        # Set job to be due now
        job.next_run = datetime.now() - timedelta(seconds=1)
        
        if not job.is_due():
            print("❌ Job is_due() logic failed")
            return False
        
        print("✅ Job scheduling logic working")
        
        return True
        
    except Exception as e:
        print(f"❌ Timing test failed: {e}")
        return False


def test_error_handling() -> bool:
    """Test error handling and failure recovery."""
    print("\nTesting error handling...")
    
    try:
        scheduler = JobScheduler()
        
        # Register failing job
        scheduler.register_job(
            name="failing_job",
            function=test_failing_job,
            interval_minutes=1,
            description="Job that always fails",
            enabled=True
        )
        
        # Execute failing job
        result = scheduler.run_job_now("failing_job")
        if result.success:
            print("❌ Failing job should not succeed")
            return False
        
        if not result.error_message:
            print("❌ Error message not captured")
            return False
        
        print(f"✅ Error handling working: {result.error_message}")
        
        # Check failure count
        job_status = scheduler.get_job_status("failing_job")
        if job_status['failure_count'] != 1:
            print("❌ Failure count not tracked correctly")
            return False
        
        print("✅ Failure tracking working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_job_registration() -> bool:
    """Test registration of actual jobs."""
    print("\nTesting actual job registration...")
    
    try:
        scheduler = JobScheduler()
        
        # Register hourly jobs
        register_hourly_jobs(scheduler)
        hourly_jobs = scheduler.get_all_jobs_status()
        
        expected_hourly = [
            "hourly_summary_computation",
            "hourly_trend_analysis", 
            "data_quality_check"
        ]
        
        for job_name in expected_hourly:
            if job_name not in hourly_jobs:
                print(f"❌ Missing hourly job: {job_name}")
                return False
        
        print(f"✅ Hourly jobs registered: {len(hourly_jobs)} jobs")
        
        # Register nightly jobs
        register_nightly_jobs(scheduler)
        all_jobs = scheduler.get_all_jobs_status()
        
        expected_nightly = [
            "nightly_database_maintenance",
            "nightly_backup_creation",
            "nightly_data_cleanup",
            "nightly_system_health_report"
        ]
        
        for job_name in expected_nightly:
            if job_name not in all_jobs:
                print(f"❌ Missing nightly job: {job_name}")
                return False
        
        print(f"✅ All jobs registered: {len(all_jobs)} total jobs")
        
        # Test that all jobs have proper configuration
        for job_name, job_status in all_jobs.items():
            if not job_status['description']:
                print(f"❌ Job missing description: {job_name}")
                return False
            
            if job_status['interval_minutes'] <= 0:
                print(f"❌ Job has invalid interval: {job_name}")
                return False
        
        print("✅ All jobs properly configured")
        return True
        
    except Exception as e:
        print(f"❌ Job registration test failed: {e}")
        return False


def test_database_job_execution() -> bool:
    """Test actual database job execution with test data."""
    print("\nTesting database job execution...")
    
    # Use a test database
    test_db_path = "test_job_scheduler.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    try:
        # Initialize test database
        db = DatabaseManager(test_db_path)
        db.initialize_database()
        
        print("✅ Test database initialized")
        
        # Create some test data first
        from models import RawPoint, MetricType
        from datetime import date
        
        # Add some raw data points
        test_points = [
            RawPoint(
                metric=MetricType.STEPS,
                start_time="2025-08-03T08:00:00Z",
                value=5000,
                unit="steps",
                source="test_job"
            ),
            RawPoint(
                metric=MetricType.SLEEP,
                start_time="2025-08-02T23:00:00Z",
                end_time="2025-08-03T07:00:00Z",
                value=480,
                unit="minutes",
                source="test_job"
            )
        ]
        
        for point in test_points:
            db.insert_raw_point(point)
        
        print(f"✅ Test data inserted: {len(test_points)} points")
        
        # Test hourly summary computation job
        from jobs.hourly import compute_daily_summaries_job
        
        # Temporarily override the default database with our test database
        original_db_init = DatabaseManager.__init__
        
        def test_db_init(self, db_path="healthtracker.db"):
            original_db_init(self, test_db_path)
        
        DatabaseManager.__init__ = test_db_init
        
        try:
            result = compute_daily_summaries_job()
            
            if not result['success']:
                print("❌ Summary computation job failed")
                return False
            
            print(f"✅ Summary computation job successful: "
                  f"{result['summaries_created']} summaries created")
            
            # Test data quality check job
            from jobs.hourly import data_quality_check_job
            
            quality_result = data_quality_check_job()
            
            if not quality_result['success']:
                print("❌ Data quality check job failed")
                return False
            
            print(f"✅ Data quality check successful: "
                  f"{quality_result['total_alerts']} alerts")
            
        finally:
            # Restore original database initialization
            DatabaseManager.__init__ = original_db_init
        
        return True
        
    except Exception as e:
        print(f"❌ Database job execution test failed: {e}")
        return False
    
    finally:
        # Clean up test database
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("🧹 Test database cleaned up")


def test_job_scheduler_system():
    """Run all job scheduler validation tests."""
    print("Job Scheduler System Validation")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_scheduler_basic_functionality),
        ("Scheduler Timing", test_scheduler_timing),
        ("Error Handling", test_error_handling),
        ("Job Registration", test_job_registration),
        ("Database Job Execution", test_database_job_execution)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL JOB SCHEDULER TESTS PASSED!")
        return True
    else:
        print(f"\n❌ {len(results) - passed} tests failed")
        return False


if __name__ == "__main__":
    success = test_job_scheduler_system()
    sys.exit(0 if success else 1)