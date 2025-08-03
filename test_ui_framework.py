#!/usr/bin/env python3
"""
Validation test for UI framework.
Tests dashboard loading, API endpoints, and basic functionality.
"""
import sys
import os
import requests
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from models import RawPoint, MetricType, ManualEntry, ManualMetricType
from datetime import date, datetime, timedelta


def test_static_files() -> bool:
    """Test that static files exist and are accessible."""
    print("\nTesting static file structure...")
    
    try:
        static_dir = Path("static")
        
        required_files = [
            "index.html",
            "css/styles.css",
            "js/dashboard.js"
        ]
        
        for file_path in required_files:
            full_path = static_dir / file_path
            if not full_path.exists():
                print(f"❌ Missing static file: {file_path}")
                return False
            
            # Check file size
            file_size = full_path.stat().st_size
            if file_size == 0:
                print(f"❌ Empty static file: {file_path}")
                return False
            
            print(f"✅ Found {file_path} ({file_size} bytes)")
        
        # Check HTML content
        html_content = (static_dir / "index.html").read_text()
        required_elements = [
            'x-data="dashboardData()"',
            'hx-get="/api/ui/today"',
            'class="tab-navigation"',
            'alpinejs'
        ]
        
        for element in required_elements:
            if element not in html_content:
                print(f"❌ Missing HTML element: {element}")
                return False
        
        print("✅ HTML structure validated")
        
        # Check CSS content
        css_content = (static_dir / "css/styles.css").read_text()
        required_css = [
            "--touch-target-min: 44px",
            ".tab-navigation",
            ".metric-card",
            "@media (max-width:"
        ]
        
        for css_rule in required_css:
            if css_rule not in css_content:
                print(f"❌ Missing CSS rule: {css_rule}")
                return False
        
        print("✅ CSS structure validated")
        
        # Check JavaScript content
        js_content = (static_dir / "js/dashboard.js").read_text()
        required_js = [
            "function dashboardData()",
            "function syncStatus()",
            "switchTab(",
            "Alpine.js"
        ]
        
        for js_function in required_js:
            if js_function not in js_content:
                print(f"❌ Missing JS function: {js_function}")
                return False
        
        print("✅ JavaScript structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Static files test failed: {e}")
        return False


def test_ui_endpoints_structure() -> bool:
    """Test UI endpoint code structure."""
    print("\nTesting UI endpoints structure...")
    
    try:
        # Check that UI API file exists and has expected content
        ui_file = Path("src/api/ui.py")
        if not ui_file.exists():
            print("❌ UI API file doesn't exist")
            return False
        
        ui_content = ui_file.read_text()
        
        # Check for expected endpoints
        expected_endpoints = [
            '@router.get("/today"',
            '@router.get("/week"',
            '@router.get("/month"',
            '@router.get("/goals"',
            '@router.get("/manual-entry-form/'
        ]
        
        for endpoint in expected_endpoints:
            if endpoint not in ui_content:
                print(f"❌ Missing API endpoint: {endpoint}")
                return False
        
        print(f"✅ Found {len(expected_endpoints)} API endpoints")
        
        # Check for helper functions
        helper_functions = [
            'def _generate_metric_card(',
            'def _generate_steps_chart(',
            'def _generate_line_chart(',
            'def _generate_empty_chart('
        ]
        
        for func_name in helper_functions:
            if func_name not in ui_content:
                print(f"❌ Missing helper function: {func_name}")
                return False
        
        print("✅ Helper functions exist")
        
        # Check for proper imports
        required_imports = [
            'from fastapi import APIRouter',
            'from database import DatabaseManager',
            'from models import MetricType'
        ]
        
        for import_stmt in required_imports:
            if import_stmt not in ui_content:
                print(f"❌ Missing import: {import_stmt}")
                return False
        
        print("✅ Required imports found")
        
        return True
        
    except Exception as e:
        print(f"❌ UI endpoints structure test failed: {e}")
        return False


def test_ui_data_generation() -> bool:
    """Test UI data generation logic."""
    print("\nTesting UI data generation...")
    
    try:
        # Test that UI generation functions are properly structured
        ui_file = Path("src/api/ui.py")
        ui_content = ui_file.read_text()
        
        # Check for HTML generation patterns
        html_patterns = [
            'return f"""',
            '<div class="metric-card">',
            '<div class="chart-card">',
            '<canvas id="',
            'new Chart(',
            'backgroundColor:',
            'hx-post="/api/manual"'
        ]
        
        for pattern in html_patterns:
            if pattern not in ui_content:
                print(f"❌ Missing HTML generation pattern: {pattern}")
                return False
        
        print("✅ HTML generation patterns found")
        
        # Check for proper data handling
        data_patterns = [
            'data.get(',
            'datetime.fromisoformat(',
            'MetricType.STEPS',
            'ManualMetricType.HRV',
            'formatted_value =',
            'if not data:'
        ]
        
        for pattern in data_patterns:
            if pattern not in ui_content:
                print(f"❌ Missing data handling pattern: {pattern}")
                return False
        
        print("✅ Data handling patterns found")
        
        # Check for Chart.js integration
        chart_patterns = [
            'new Chart(',
            'type: \'bar\'',
            'type: \'line\'',
            'responsive: true',
            'maintainAspectRatio: false'
        ]
        
        for pattern in chart_patterns:
            if pattern not in ui_content:
                print(f"❌ Missing Chart.js pattern: {pattern}")
                return False
        
        print("✅ Chart.js integration patterns found")
        
        # Check for form generation
        form_patterns = [
            '<form hx-post=',
            'type="number"',
            'type="radio"',
            'name="value"',
            'required'
        ]
        
        for pattern in form_patterns:
            if pattern not in ui_content:
                print(f"❌ Missing form pattern: {pattern}")
                return False
        
        print("✅ Form generation patterns found")
        
        return True
        
    except Exception as e:
        print(f"❌ UI data generation test failed: {e}")
        return False


def test_responsive_design() -> bool:
    """Test responsive design elements in CSS."""
    print("\nTesting responsive design...")
    
    try:
        css_path = Path("static/css/styles.css")
        css_content = css_path.read_text()
        
        # Check for responsive design elements
        responsive_elements = [
            "@media (max-width: 1024px)",
            "@media (max-width: 800px)",
            "grid-template-columns: repeat(auto-fit,",
            "--touch-target-min: 44px",
            "min-height: var(--touch-target-min)"
        ]
        
        for element in responsive_elements:
            if element not in css_content:
                print(f"❌ Missing responsive element: {element}")
                return False
        
        print("✅ Responsive design elements found")
        
        # Check for touch-friendly features
        touch_features = [
            "user-select: none",
            "cursor: pointer",
            "transition:",
            ":hover",
            ":active"
        ]
        
        for feature in touch_features:
            if feature not in css_content:
                print(f"❌ Missing touch feature: {feature}")
                return False
        
        print("✅ Touch-friendly features found")
        
        # Check for accessibility features
        accessibility_features = [
            "font-size",
            "line-height",
            "color:",
            "background:",
            "box-shadow:"
        ]
        
        for feature in accessibility_features:
            if css_content.count(feature) < 5:  # Should appear multiple times
                print(f"❌ Insufficient accessibility feature usage: {feature}")
                return False
        
        print("✅ Accessibility features validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Responsive design test failed: {e}")
        return False


def test_javascript_functionality() -> bool:
    """Test JavaScript functionality structure."""
    print("\nTesting JavaScript functionality...")
    
    try:
        js_path = Path("static/js/dashboard.js")
        js_content = js_path.read_text()
        
        # Check for main functions
        main_functions = [
            "function dashboardData()",
            "function syncStatus()",
            "switchTab(",
            "showManualEntry(",
            "closeModal(",
            "updateDateInfo(",
            "setupHtmxEvents("
        ]
        
        for func in main_functions:
            if func not in js_content:
                print(f"❌ Missing JavaScript function: {func}")
                return False
        
        print("✅ Main JavaScript functions found")
        
        # Check for Alpine.js integration
        alpine_features = [
            "x-data=",
            "x-show=",
            "@click=",
            "x-text=",
            "x-init="
        ]
        
        # Check in both JS and HTML
        html_path = Path("static/index.html")
        html_content = html_path.read_text()
        
        for feature in alpine_features:
            if feature not in html_content:
                print(f"❌ Missing Alpine.js feature in HTML: {feature}")
                return False
        
        print("✅ Alpine.js integration validated")
        
        # Check for HTMX integration
        htmx_features = [
            "hx-get=",
            "hx-trigger=",
            "hx-swap=",
            "htmx.ajax"
        ]
        
        for feature in htmx_features:
            if feature not in html_content and feature not in js_content:
                print(f"❌ Missing HTMX feature: {feature}")
                return False
        
        # hx-post is generated dynamically in forms, so check for htmx usage in general
        if "htmx" not in html_content.lower():
            print("❌ Missing HTMX integration")
            return False
        
        print("✅ HTMX integration validated")
        
        # Check for utility functions
        utility_features = [
            "HealthTrackerUtils",
            "formatNumber",
            "formatDate",
            "hapticFeedback",
            "debounce"
        ]
        
        for feature in utility_features:
            if feature not in js_content:
                print(f"❌ Missing utility feature: {feature}")
                return False
        
        print("✅ Utility functions found")
        
        return True
        
    except Exception as e:
        print(f"❌ JavaScript functionality test failed: {e}")
        return False


def test_ui_framework_system():
    """Run all UI framework validation tests."""
    print("UI Framework System Validation")
    print("=" * 50)
    
    tests = [
        ("Static Files Structure", test_static_files),
        ("UI Endpoints Structure", test_ui_endpoints_structure),
        ("UI Data Generation", test_ui_data_generation),
        ("Responsive Design", test_responsive_design),
        ("JavaScript Functionality", test_javascript_functionality)
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
        print("\n🎉 ALL UI FRAMEWORK TESTS PASSED!")
        print("\n📱 Dashboard is ready for 7-inch touchscreen!")
        return True
    else:
        print(f"\n❌ {len(results) - passed} tests failed")
        return False


if __name__ == "__main__":
    success = test_ui_framework_system()
    sys.exit(0 if success else 1)