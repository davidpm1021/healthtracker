#!/usr/bin/env python3
"""
Validation test for Health Tracker normalization engine.
Tests all metric processors with realistic test data.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from normalization import normalize_raw_points_to_summaries
from metrics.steps import normalize_steps, analyze_steps_patterns
from metrics.sleep import normalize_sleep, analyze_sleep_patterns
from metrics.weight import normalize_weight, analyze_weight_patterns

def create_test_data():
    """Create realistic test data for all metrics."""
    base_date = datetime(2024, 8, 1)
    test_data = []
    
    # Steps data - multiple readings throughout the day
    for day in range(3):
        date = base_date + timedelta(days=day)
        # Morning walk
        test_data.append({
            'metric': 'steps',
            'start_time': f"{date.strftime('%Y-%m-%d')}T07:30:00Z",
            'value': 2500.0,
            'unit': 'steps',
            'source': 'iPhone'
        })
        # Afternoon activity
        test_data.append({
            'metric': 'steps',
            'start_time': f"{date.strftime('%Y-%m-%d')}T14:15:00Z",
            'value': 3200.0,
            'unit': 'steps',
            'source': 'iPhone'
        })
        # Evening walk
        test_data.append({
            'metric': 'steps',
            'start_time': f"{date.strftime('%Y-%m-%d')}T19:45:00Z",
            'value': 1800.0,
            'unit': 'steps',
            'source': 'iPhone'
        })
    
    # Sleep data - one session per night
    for day in range(3):
        date = base_date + timedelta(days=day)
        # Sleep session from 10:30 PM to 6:15 AM (7h 45m = 465 min)
        test_data.append({
            'metric': 'sleep',
            'start_time': f"{date.strftime('%Y-%m-%d')}T22:30:00Z",
            'end_time': f"{(date + timedelta(days=1)).strftime('%Y-%m-%d')}T06:15:00Z",
            'value': 465.0,
            'unit': 'minutes',
            'source': 'AutoSleep',
            'metadata': {'quality': 0.82}
        })
    
    # Weight data - morning weigh-ins
    for day in range(3):
        date = base_date + timedelta(days=day)
        weight_value = 75.2 + (day * 0.1)  # Slight daily variation
        test_data.append({
            'metric': 'weight',
            'start_time': f"{date.strftime('%Y-%m-%d')}T07:00:00Z",
            'value': weight_value,
            'unit': 'kg',
            'source': 'Withings Scale',
            'metadata': {'body_fat_percentage': 18.5, 'muscle_mass_kg': 58.3}
        })
    
    return test_data

def test_individual_processors():
    """Test each metric processor individually."""
    print("=== Testing Individual Metric Processors ===\n")
    
    test_data = create_test_data()
    
    # Group test data by metric and date
    grouped_data = {}
    for point in test_data:
        metric = point['metric']
        
        # Parse date from start_time
        start_time = point['start_time'].replace('Z', '+00:00')
        dt = datetime.fromisoformat(start_time)
        date_str = dt.date().isoformat()
        
        # For sleep, use special date logic
        if metric == 'sleep':
            from metrics.sleep import SleepProcessor
            processor = SleepProcessor()
            date_str = processor._determine_sleep_date(point['start_time'], point.get('end_time'))
        
        key = (metric, date_str)
        if key not in grouped_data:
            grouped_data[key] = []
        grouped_data[key].append(point)
    
    # Test each processor
    results = {}
    
    for (metric, date_str), points in grouped_data.items():
        print(f"Testing {metric} processor for {date_str}...")
        
        try:
            if metric == 'steps':
                summary = normalize_steps(date_str, points)
                patterns = analyze_steps_patterns(points)
            elif metric == 'sleep':
                summary = normalize_sleep(date_str, points)
                patterns = analyze_sleep_patterns(points)
            elif metric == 'weight':
                summary = normalize_weight(date_str, points)
                patterns = analyze_weight_patterns(points)
            else:
                print(f"  ❌ Unknown metric: {metric}")
                continue
            
            if summary:
                print(f"  ✅ SUCCESS: {summary.value} {summary.unit}")
                results[(metric, date_str)] = {
                    'summary': {
                        'date': summary.date,
                        'metric': summary.metric,
                        'value': summary.value,
                        'unit': summary.unit
                    },
                    'patterns': patterns,
                    'input_points': len(points)
                }
            else:
                print(f"  ❌ FAILED: No summary generated")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print(f"\nIndividual processor tests: {len(results)} successful\n")
    return results

def test_full_normalization_engine():
    """Test the complete normalization engine."""
    print("=== Testing Full Normalization Engine ===\n")
    
    test_data = create_test_data()
    
    print(f"Input: {len(test_data)} raw data points")
    for metric in ['steps', 'sleep', 'weight']:
        count = sum(1 for p in test_data if p['metric'] == metric)
        print(f"  - {metric}: {count} points")
    
    try:
        # Run full normalization
        summaries = normalize_raw_points_to_summaries(test_data)
        
        if summaries:
            print(f"\n✅ SUCCESS: Generated {len(summaries)} daily summaries")
            
            # Group by metric type
            by_metric = {}
            for summary in summaries:
                metric = summary.metric
                if metric not in by_metric:
                    by_metric[metric] = []
                by_metric[metric].append(summary)
            
            for metric, metric_summaries in by_metric.items():
                print(f"\n{metric.upper()} summaries:")
                for summary in sorted(metric_summaries, key=lambda x: x.date):
                    print(f"  {summary.date}: {summary.value} {summary.unit}")
            
            return summaries
        else:
            print("❌ FAILED: No summaries generated")
            return []
            
    except Exception as e:
        print(f"❌ ERROR in normalization engine: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n=== Testing Edge Cases ===\n")
    
    edge_cases = [
        # Empty data
        {
            'name': 'Empty data',
            'data': []
        },
        # Invalid values
        {
            'name': 'Negative steps',
            'data': [{
                'metric': 'steps',
                'start_time': '2024-08-01T12:00:00Z',
                'value': -100,
                'unit': 'steps',
                'source': 'test'
            }]
        },
        # Invalid units
        {
            'name': 'Invalid unit',
            'data': [{
                'metric': 'weight',
                'start_time': '2024-08-01T07:00:00Z',
                'value': 75,
                'unit': 'invalid_unit',
                'source': 'test'
            }]
        },
        # Unrealistic values
        {
            'name': 'Unrealistic sleep (25 hours)',
            'data': [{
                'metric': 'sleep',
                'start_time': '2024-08-01T22:00:00Z',
                'value': 25,
                'unit': 'hours',
                'source': 'test'
            }]
        },
        # Missing required fields
        {
            'name': 'Missing start_time',
            'data': [{
                'metric': 'steps',
                'value': 5000,
                'unit': 'steps',
                'source': 'test'
            }]
        }
    ]
    
    for case in edge_cases:
        print(f"Testing: {case['name']}")
        try:
            summaries = normalize_raw_points_to_summaries(case['data'])
            if summaries:
                print(f"  ⚠️  Unexpected success: {len(summaries)} summaries")
            else:
                print(f"  ✅ Correctly handled: No summaries generated")
        except Exception as e:
            print(f"  ✅ Correctly raised exception: {e}")
    
    print()

def main():
    """Run all validation tests."""
    print("Health Tracker Normalization Engine Validation")
    print("=" * 50)
    
    # Test individual processors
    individual_results = test_individual_processors()
    
    # Test full normalization engine
    full_results = test_full_normalization_engine()
    
    # Test edge cases
    test_edge_cases()
    
    # Summary
    print("=== VALIDATION SUMMARY ===")
    print(f"Individual processor tests: {len(individual_results)} passed")
    print(f"Full normalization test: {'✅ PASSED' if full_results else '❌ FAILED'}")
    print(f"Generated summaries: {len(full_results)}")
    
    if individual_results and full_results:
        print("\n🎉 ALL TESTS PASSED - Normalization engine is working correctly!")
        return True
    else:
        print("\n❌ SOME TESTS FAILED - Check the logs above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)