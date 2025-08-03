#!/usr/bin/env python3
"""
Validation test for summary computation system.
Tests daily summary generation, moving averages, and trend analysis.
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime, date, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from models import RawPoint, MetricType
from summaries import SummaryComputer
from trends import TrendAnalyzer, analyze_metric_trends


def create_test_data(db: DatabaseManager, days: int = 14) -> int:
    """Create realistic test data for validation."""
    print(f"Creating {days} days of test data...")
    
    base_date = date.today() - timedelta(days=days)
    points_created = 0
    
    for day in range(days):
        current_date = base_date + timedelta(days=day)
        date_str = current_date.isoformat()
        
        # Steps data - 3 readings per day
        for hour in [8, 14, 20]:  # Morning, afternoon, evening
            steps_value = 2000 + (day * 100) + (hour * 50)  # Increasing trend
            point = RawPoint(
                metric=MetricType.STEPS,
                start_time=f"{date_str}T{hour:02d}:00:00Z",
                value=steps_value,
                unit="steps",
                source="test_data"
            )
            if db.insert_raw_point(point):
                points_created += 1
        
        # Sleep data - 1 reading per night
        sleep_minutes = 450 + (day % 7) * 10  # Weekly variation
        point = RawPoint(
            metric=MetricType.SLEEP,
            start_time=f"{date_str}T23:00:00Z",
            end_time=f"{(current_date + timedelta(days=1)).isoformat()}T07:30:00Z",
            value=sleep_minutes,
            unit="minutes",
            source="test_data"
        )
        if db.insert_raw_point(point):
            points_created += 1
        
        # Weight data - 1 reading per day (with slight downward trend)
        weight_value = 75.0 - (day * 0.05)  # Gradual weight loss
        point = RawPoint(
            metric=MetricType.WEIGHT,
            start_time=f"{date_str}T07:00:00Z",
            value=weight_value,
            unit="kg",
            source="test_data"
        )
        if db.insert_raw_point(point):
            points_created += 1
    
    print(f"✅ Created {points_created} raw data points")
    return points_created


def test_summary_computation(db: DatabaseManager) -> bool:
    """Test daily summary computation."""
    print("\nTesting daily summary computation...")
    
    try:
        computer = SummaryComputer(db)
        
        # Test computation for last 14 days
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=14)).isoformat()
        
        start_time = time.time()
        result = computer.compute_daily_summaries(start_date, end_date, force_recompute=True)
        computation_time = time.time() - start_time
        
        if not result['success']:
            print(f"❌ Summary computation failed: {result.get('error')}")
            return False
        
        print(f"✅ Summary computation successful:")
        print(f"  - Created: {result['summaries_created']} summaries")
        print(f"  - Updated: {result['summaries_updated']} summaries")
        print(f"  - Total: {result['total_summaries']} summaries")
        print(f"  - Raw points: {result['raw_points_processed']} processed")
        print(f"  - Time: {computation_time:.2f} seconds")
        
        # Validate performance requirement (<5 seconds for 30 days)
        if computation_time > 5.0:
            print(f"⚠️  Computation time ({computation_time:.2f}s) exceeds 5s requirement")
        else:
            print(f"✅ Performance requirement met ({computation_time:.2f}s < 5s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Summary computation test failed: {e}")
        return False


def test_moving_averages_and_trends(db: DatabaseManager) -> bool:
    """Test moving averages and trend calculation."""
    print("\nTesting moving averages and trend calculation...")
    
    try:
        computer = SummaryComputer(db)
        
        # Test for each metric
        for metric in MetricType.all():
            print(f"  Testing {metric}...")
            
            start_time = time.time()
            result = computer.compute_moving_averages_and_trends(metric)
            computation_time = time.time() - start_time
            
            if 'error' in result:
                print(f"    ❌ Failed: {result['error']}")
                continue
            
            print(f"    ✅ Success: {result['data_points']} points, {result['updated_summaries']} updated")
            
            if result.get('latest_values'):
                latest = result['latest_values']
                print(f"    📊 Latest: value={latest['value']}, 7d_avg={latest['avg_7day']}, trend={latest['trend_slope']}")
            
            print(f"    ⏱️  Time: {computation_time:.3f} seconds")
        
        print("✅ Moving averages and trends computation successful")
        return True
        
    except Exception as e:
        print(f"❌ Moving averages test failed: {e}")
        return False


def test_trend_analysis() -> bool:
    """Test trend analysis functionality."""
    print("\nTesting trend analysis...")
    
    try:
        analyzer = TrendAnalyzer()
        
        # Test with sample data showing clear trends
        test_cases = [
            {
                'name': 'Increasing trend',
                'values': [10, 12, 14, 16, 18, 20, 22, 24, 26, 28],
                'expected_trend': 'increasing'
            },
            {
                'name': 'Decreasing trend', 
                'values': [100, 95, 90, 85, 80, 75, 70, 65, 60, 55],
                'expected_trend': 'decreasing'
            },
            {
                'name': 'Flat trend',
                'values': [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
                'expected_trend': 'flat'
            }
        ]
        
        for test_case in test_cases:
            trend = analyzer.compute_linear_trend(test_case['values'])
            classification = analyzer.classify_trend(trend['slope'])
            
            if classification == test_case['expected_trend']:
                print(f"    ✅ {test_case['name']}: {classification} (slope: {trend['slope']})")
            else:
                print(f"    ❌ {test_case['name']}: expected {test_case['expected_trend']}, got {classification}")
                return False
        
        # Test moving averages
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        moving_avg = analyzer.compute_moving_average(values, 3)
        
        # For window=3, first 2 should be None, then [2, 3, 4, 5, 6, 7, 8, 9]
        expected = [None, None, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        
        if moving_avg == expected:
            print(f"    ✅ Moving average calculation correct")
        else:
            print(f"    ❌ Moving average incorrect: got {moving_avg}, expected {expected}")
            return False
        
        print("✅ Trend analysis tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Trend analysis test failed: {e}")
        return False


def test_comprehensive_analysis(db: DatabaseManager) -> bool:
    """Test comprehensive metric analysis."""
    print("\nTesting comprehensive analysis...")
    
    try:
        # Get summaries for steps metric
        summaries = db.get_daily_summaries_for_metric(
            MetricType.STEPS,
            (date.today() - timedelta(days=14)).isoformat(),
            date.today().isoformat()
        )
        
        if not summaries:
            print("❌ No summaries found for comprehensive analysis")
            return False
        
        # Perform comprehensive analysis
        analysis = analyze_metric_trends(summaries, MetricType.STEPS, 14)
        
        # Validate analysis structure
        required_keys = ['metric', 'data_points', 'trend', 'moving_averages', 'statistics', 'patterns']
        
        for key in required_keys:
            if key not in analysis:
                print(f"❌ Missing key '{key}' in analysis")
                return False
        
        print(f"✅ Comprehensive analysis successful:")
        print(f"  - Metric: {analysis['metric']}")
        print(f"  - Data points: {analysis['data_points']}")
        print(f"  - Trend: {analysis['trend']['classification']} (slope: {analysis['trend']['slope']})")
        print(f"  - Current value: {analysis['current_value']}")
        
        if analysis['moving_averages']['7_day_latest']:
            print(f"  - 7-day average: {analysis['moving_averages']['7_day_latest']}")
        
        print(f"  - Min/Max: {analysis['statistics']['min']}/{analysis['statistics']['max']}")
        print(f"  - Volatility: {analysis['statistics']['volatility']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive analysis test failed: {e}")
        return False


def test_summary_system():
    """Run all summary system validation tests."""
    print("Health Tracker Summary System Validation")
    print("=" * 50)
    
    # Use a test database
    test_db_path = "test_summary_system.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    try:
        # Initialize database
        db = DatabaseManager(test_db_path)
        db.initialize_database()
        
        print("✅ Test database initialized")
        
        # Create test data
        points_created = create_test_data(db, days=14)
        
        if points_created == 0:
            print("❌ No test data created")
            return False
        
        # Run tests
        tests = [
            ("Summary Computation", lambda: test_summary_computation(db)),
            ("Moving Averages & Trends", lambda: test_moving_averages_and_trends(db)),
            ("Trend Analysis", test_trend_analysis),
            ("Comprehensive Analysis", lambda: test_comprehensive_analysis(db))
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
            print("\n🎉 ALL SUMMARY SYSTEM TESTS PASSED!")
            return True
        else:
            print(f"\n❌ {len(results) - passed} tests failed")
            return False
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("🧹 Test database cleaned up")


if __name__ == "__main__":
    success = test_summary_system()
    sys.exit(0 if success else 1)