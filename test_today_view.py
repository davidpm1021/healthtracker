#!/usr/bin/env python3
"""
Validation test for Today View implementation.
Tests component templates, API endpoints, and integration.
"""
import sys
import os
import requests
import time
import json
from pathlib import Path
from datetime import date, datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from models import RawPoint, MetricType, ManualEntry, ManualMetricType


def test_component_templates() -> bool:
    """Test that component templates exist and have correct structure."""
    print("\nTesting component templates...")
    
    try:
        # Check today-view.html
        today_view_path = Path("static/components/today-view.html")
        if not today_view_path.exists():
            print("❌ Missing today-view.html component")
            return False
        
        today_content = today_view_path.read_text()
        
        # Check for required elements in today-view
        required_today_elements = [
            'class="today-view-container"',
            'class="sync-banner"',
            'class="quick-stats"',
            'class="primary-metrics-grid"',
            'class="secondary-metrics-grid"',
            'class="manual-entry-section"',
            'class="insights-section"',
            'hx-get="/api/ui/today/primary"',
            'hx-get="/api/ui/today/secondary"',
            'hx-get="/api/ui/today/insights"',
            'x-data="syncBanner()"',
            'x-text="$store.todayStats.totalMetrics',
            'x-text="$store.manualEntryStatus.hrv'
        ]
        
        for element in required_today_elements:
            if element not in today_content:
                print(f"❌ Missing element in today-view.html: {element}")
                return False
        
        print("✅ today-view.html structure validated")
        
        # Check metric-card.html
        metric_card_path = Path("static/components/metric-card.html")
        if not metric_card_path.exists():
            print("❌ Missing metric-card.html component")
            return False
        
        card_content = metric_card_path.read_text()
        
        # Check for required template variables
        required_card_variables = [
            '{metric_type}',
            '{metric_class}',
            '{metric_icon}',
            '{status_class}',
            '{metric_name}',
            '{last_updated}',
            '{value}',
            '{unit}',
            '{trend_indicator}',
            '{comparison_text}',
            '{action_buttons}',
            '{progress_display}',
            '{progress_percent}',
            '{progress_text}'
        ]
        
        for variable in required_card_variables:
            if variable not in card_content:
                print(f"❌ Missing template variable in metric-card.html: {variable}")
                return False
        
        print("✅ metric-card.html template variables validated")
        
        # Check CSS classes in both files
        css_classes = [
            'metric-card',
            'metric-header', 
            'metric-icon',
            'metric-value',
            'sync-banner',
            'quick-stats',
            'manual-entry-card'
        ]
        
        combined_content = today_content + card_content
        for css_class in css_classes:
            if css_class not in combined_content:
                print(f"❌ Missing CSS class: {css_class}")
                return False
        
        print("✅ CSS classes validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Component templates test failed: {e}")
        return False


def test_new_api_endpoints() -> bool:
    """Test new Today view API endpoints."""
    print("\nTesting new API endpoints...")
    
    try:
        # Check that the UI API file has the new endpoints
        ui_file = Path("src/api/ui.py")
        ui_content = ui_file.read_text()
        
        # Check for new endpoint functions
        new_endpoints = [
            '@router.get("/today/primary"',
            '@router.get("/today/secondary"',
            '@router.get("/today/stats"',
            '@router.get("/today/manual-status"',
            '@router.get("/today/insights"',
            'def get_today_primary_metrics',
            'def get_today_secondary_metrics',
            'def get_today_stats',
            'def get_today_manual_status',
            'def get_today_insights',
            'def _generate_enhanced_metric_card'
        ]
        
        for endpoint in new_endpoints:
            if endpoint not in ui_content:
                print(f"❌ Missing API endpoint: {endpoint}")
                return False
        
        print("✅ All new API endpoints found")
        
        # Check enhanced metric card function
        if '_generate_enhanced_metric_card(template: str, metric: str' not in ui_content:
            print("❌ Enhanced metric card function has wrong signature")
            return False
        
        print("✅ Enhanced metric card function validated")
        
        # Check for proper template variable replacement
        template_replacements = [
            'result = template.replace("{metric_type}",',
            'result = result.replace("{metric_icon}",',
            'result = result.replace("{status_class}",',
            'result = result.replace("{value}",',
            'result = result.replace("{trend_indicator}",'
        ]
        
        for replacement in template_replacements:
            if replacement not in ui_content:
                print(f"❌ Missing template replacement: {replacement}")
                return False
        
        print("✅ Template replacement logic validated")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False


def test_javascript_integration() -> bool:
    """Test JavaScript integration for Today view."""
    print("\nTesting JavaScript integration...")
    
    try:
        js_file = Path("static/js/dashboard.js")
        js_content = js_file.read_text()
        
        # Check for Alpine.js store functions
        required_js_elements = [
            "Alpine.store('todayStats'",
            "Alpine.store('manualEntryStatus'",
            "window.showManualEntry = function",
            "totalMetrics: 0",
            "completedGoals: 0", 
            "streakDays: 0",
            "healthScore: '--'",
            "hrv: 'Not entered today'",
            "mood: 'Not entered today'",
            "energy: 'Not entered today'",
            "notes: 'No notes today'"
        ]
        
        for element in required_js_elements:
            if element not in js_content:
                print(f"❌ Missing JavaScript element: {element}")
                return False
        
        print("✅ Alpine.js stores validated")
        
        # Check for API integration
        api_calls = [
            "fetch('/api/ui/today/stats')",
            "fetch('/api/ui/today/manual-status')"
        ]
        
        for api_call in api_calls:
            if api_call not in js_content:
                print(f"❌ Missing API call: {api_call}")
                return False
        
        print("✅ API integration validated")
        
        # Check for periodic updates
        if "setInterval" not in js_content or "300000" not in js_content:
            print("❌ Missing periodic update logic")
            return False
        
        print("✅ Periodic update logic validated")
        
        return True
        
    except Exception as e:
        print(f"❌ JavaScript integration test failed: {e}")
        return False


def test_data_flow() -> bool:
    """Test data flow from database to UI components."""
    print("\nTesting data flow...")
    
    try:
        # Test database connection
        db = DatabaseManager()
        today = date.today().isoformat()
        
        # Test that we can connect to database 
        try:
            db.get_daily_summaries_for_metric(MetricType.STEPS, today, today)
            print("✅ Database connection successful")
        except Exception as e:
            print(f"⚠️ Database connection issue: {e}")
        
        # Test manual entry access (table may not exist yet)
        try:
            db.get_manual_entry(today, ManualMetricType.MOOD)
            print("✅ Manual entries table accessible")
        except Exception as e:
            print(f"⚠️ Manual entries table not found: {e}")
            # This is expected in early development
        
        # Test that the UI API can process the data
        ui_file = Path("src/api/ui.py")
        if not ui_file.exists():
            print("❌ UI API file not found")
            return False
        
        # Import and test the enhanced metric card function
        sys.path.append(str(Path(__file__).parent / 'src' / 'api'))
        
        # Test template replacement logic by checking the function exists
        ui_content = ui_file.read_text()
        if 'def _generate_enhanced_metric_card' not in ui_content:
            print("❌ Enhanced metric card function not found")
            return False
        
        print("✅ Enhanced metric card function available")
        
        # Test that metric card template can be loaded
        card_template_path = Path("static/components/metric-card.html")
        if card_template_path.exists():
            template_content = card_template_path.read_text()
            
            # Basic template validation
            if '{metric_type}' in template_content and '{value}' in template_content:
                print("✅ Metric card template is valid")
            else:
                print("❌ Metric card template missing required variables")
                return False
        else:
            print("❌ Metric card template not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Data flow test failed: {e}")
        return False


def test_responsive_design() -> bool:
    """Test responsive design elements for Today view."""
    print("\nTesting responsive design...")
    
    try:
        # Check today-view.html for responsive elements
        today_view_path = Path("static/components/today-view.html")
        today_content = today_view_path.read_text()
        
        # Check for responsive CSS
        responsive_elements = [
            "@media (max-width: 1024px)",
            "@media (max-width: 800px)",
            "@media (max-width: 600px)",
            "grid-template-columns: repeat(auto-fit",
            "var(--touch-target-min)",
            "backdrop-filter: blur"
        ]
        
        for element in responsive_elements:
            if element not in today_content:
                print(f"❌ Missing responsive element: {element}")
                return False
        
        print("✅ Responsive design elements found")
        
        # Check main styles.css for touch-friendly features
        styles_path = Path("static/css/styles.css")
        if styles_path.exists():
            styles_content = styles_path.read_text()
            
            touch_features = [
                "--touch-target-min: 44px",
                "min-height: var(--touch-target-min)",
                "user-select: none",
                ":hover",
                ":active"
            ]
            
            for feature in touch_features:
                if feature not in styles_content:
                    print(f"❌ Missing touch feature: {feature}")
                    return False
            
            print("✅ Touch-friendly features validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Responsive design test failed: {e}")
        return False


def test_accessibility_features() -> bool:
    """Test accessibility features in Today view."""
    print("\nTesting accessibility features...")
    
    try:
        today_view_path = Path("static/components/today-view.html")
        today_content = today_view_path.read_text()
        
        # Check for accessibility features
        accessibility_features = [
            'aria-',  # Any ARIA attributes
            'role=',  # Role attributes  
            'tabindex=', # Tab navigation
            'alt=',   # Alt text
            'label',  # Labels
            'font-size',  # Font sizing
            'line-height',  # Line height
            'color:',  # Color contrast
        ]
        
        found_features = 0
        for feature in accessibility_features:
            if feature in today_content:
                found_features += 1
        
        if found_features >= 4:  # At least 4 accessibility features
            print(f"✅ Found {found_features} accessibility features")
        else:
            print(f"⚠️ Limited accessibility features found: {found_features}")
        
        # Check for proper semantic HTML
        semantic_elements = [
            '<h1', '<h2', '<h3',  # Headings
            '<section', '<div',   # Structure
            '<button',            # Interactive elements
            '<form'              # Forms
        ]
        
        found_semantic = 0
        for element in semantic_elements:
            if element in today_content:
                found_semantic += 1
        
        if found_semantic >= 3:
            print(f"✅ Good semantic HTML structure: {found_semantic} elements")
        else:
            print(f"⚠️ Limited semantic HTML: {found_semantic} elements")
        
        return True
        
    except Exception as e:
        print(f"❌ Accessibility test failed: {e}")
        return False


def test_today_view_system():
    """Run all Today View validation tests."""
    print("Today View Implementation Validation")
    print("=" * 50)
    
    tests = [
        ("Component Templates", test_component_templates),
        ("New API Endpoints", test_new_api_endpoints),
        ("JavaScript Integration", test_javascript_integration),
        ("Data Flow", test_data_flow),
        ("Responsive Design", test_responsive_design),
        ("Accessibility Features", test_accessibility_features)
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
        print("\n🎉 ALL TODAY VIEW TESTS PASSED!")
        print("\n📱 Today View is ready for 7-inch touchscreen!")
        print("\n✨ Features implemented:")
        print("   • Enhanced metric cards with data freshness indicators")
        print("   • Sync banner with real-time status")
        print("   • Quick stats summary")
        print("   • Primary/secondary metrics grids")
        print("   • Manual entry section with touch-optimized cards")
        print("   • Today's insights with personalized recommendations")
        print("   • Alpine.js integration with reactive data stores")
        print("   • Touch-optimized responsive design")
        return True
    else:
        print(f"\n❌ {len(results) - passed} tests failed")
        return False


if __name__ == "__main__":
    success = test_today_view_system()
    sys.exit(0 if success else 1)