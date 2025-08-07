#!/bin/bash
# Test script for Health Tracker data ingestion
# Tests the API endpoint with sample data

echo "🧪 Testing Health Tracker Ingestion API"
echo "======================================="

# Configuration
API_URL="http://192.168.86.36:8000/api/ingest"
TODAY=$(date +%Y-%m-%d)
TIMESTAMP="${TODAY}T$(date +%H:%M:%S)Z"

# Test 1: Simple steps data using "records" format (Tasker format)
echo ""
echo "Test 1: Sending steps data (records format)..."
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "metric": "steps",
        "value": 5000,
        "unit": "count",
        "start_time": "'$TIMESTAMP'"
      }
    ]
  }' \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "----------------------------------------"

# Test 2: Multiple metrics using "data_points" format (alternative format)
echo "Test 2: Sending multiple metrics (data_points format)..."
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "data_points": [
      {
        "metric": "heart_rate",
        "value": 72,
        "unit": "bpm",
        "start_time": "'$TIMESTAMP'"
      },
      {
        "metric": "weight",
        "value": 75.5,
        "unit": "kg",
        "start_time": "'$TIMESTAMP'"
      }
    ]
  }' \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "----------------------------------------"

# Test 3: Health Connect format with type field
echo "Test 3: Testing Health Connect format..."
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "type": "Steps",
        "count": 3000,
        "timestamp": "'$TIMESTAMP'"
      }
    ]
  }' \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "======================================="
echo "✅ Tests complete!"
echo ""
echo "Check the dashboard at:"
echo "http://192.168.86.36:8000/static/index.html"
echo ""
echo "Or check ingestion status at:"
echo "http://192.168.86.36:8000/api/ingest/status"