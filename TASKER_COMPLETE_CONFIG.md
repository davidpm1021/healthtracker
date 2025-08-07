# Complete Tasker Configuration for Health Data Sync

This document provides the exact Tasker configuration for your mixed automated/manual health data workflow.

## Important: JSON Format Compatibility

The HealthTracker API accepts BOTH formats:
- `"records"` array (shown in examples below) - automatically converted
- `"data_points"` array (alternative format) - native format

Both work equally well. Use whichever is easier for your Tasker setup.

## Overview

Your workflow:
- **Automated**: Steps and sleeping HR sync daily after 9pm
- **Manual**: Weight entry trigger when added to Samsung Health
- **Manual**: HRV entry via Pi touchscreen

## Profile 1: Daily Automated Sync (9pm)

**Trigger**: Time Context - 21:00 (9pm) daily

**Tasks**:
1. **Get Health Connect Data**
   - Action: Plugin → Health Connect
   - Get data for: Steps, Heart Rate
   - Date range: Today
   - Store in variables: `%STEPS`, `%HEART_RATE`

2. **HTTP POST - Send Data**
   - Action: Net → HTTP Request
   - Method: POST
   - URL: `http://192.168.86.36:8000/api/ingest`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "source": "tasker_auto",
     "date": "%DATE",
     "records": [
       {
         "metric": "steps",
         "value": %STEPS,
         "unit": "count",
         "start_time": "%DATET06:00:00.000Z",
         "end_time": "%DATET23:59:59.000Z"
       },
       {
         "metric": "heart_rate",
         "value": %HEART_RATE,
         "unit": "bpm",
         "start_time": "%DATET06:00:00.000Z",
         "end_time": "%DATET08:00:00.000Z"
       }
     ]
   }
   ```

3. **Success Notification**
   - Action: Alert → Notify
   - Title: "Health Sync Complete"
   - Text: "Steps: %STEPS, HR: %HEART_RATE bpm"

## Profile 2: Manual Weight Entry Trigger

**Trigger**: Application Event → Samsung Health (when weight data is added)

**Tasks**:
1. **Get Weight from Health Connect**
   - Action: Plugin → Health Connect
   - Get data for: Weight
   - Date range: Today
   - Store in variable: `%WEIGHT_LBS`

2. **Convert Weight to Kilograms**
   - Action: Variables → Variable Set
   - Name: `%WEIGHT_KG`
   - To: `%WEIGHT_LBS * 0.453592`
   - Do Maths: ✓

3. **HTTP POST - Send Weight**
   - Action: Net → HTTP Request
   - Method: POST
   - URL: `http://192.168.86.36:8000/api/ingest`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "source": "tasker_manual",
     "date": "%DATE",
     "records": [
       {
         "metric": "weight",
         "value": %WEIGHT_KG,
         "unit": "kg",
         "start_time": "%DATET07:00:00.000Z",
         "end_time": "%DATET07:00:00.000Z"
       }
     ]
   }
   ```

4. **Success Notification**
   - Action: Alert → Notify
   - Title: "Weight Synced"
   - Text: "%WEIGHT_LBS lbs (%WEIGHT_KG kg) sent to Pi"

## Profile 3: Test Manual Sync

**Trigger**: Manual activation (for testing)

**Tasks**:
1. **Send Test Data**
   - Action: Net → HTTP Request
   - Method: POST
   - URL: `http://192.168.86.36:8000/api/ingest`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "source": "tasker_test",
     "date": "2025-08-05",
     "records": [
       {
         "metric": "steps",
         "value": 8500,
         "unit": "count",
         "start_time": "2025-08-05T06:00:00.000Z",
         "end_time": "2025-08-05T23:59:59.000Z"
       }
     ]
   }
   ```

## Variable Setup

In Tasker, set up these variables:

1. **%DATE** = Current date in YYYY-MM-DD format
   - Formula: `%DATY-%DATM-%DATD`

2. **%DATET** = Current date for timestamps
   - Formula: `%DATY-%DATM-%DATD`

## Server Requirement

Ensure the server is running on your Pi:
```bash
ssh davidpm@192.168.86.36
cd /home/davidpm/healthtracker
python3 start_server.py
```

## Testing Steps

1. **Test the API endpoint** first:
   ```bash
   curl -X POST http://192.168.86.36:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"source":"curl_test","date":"2025-08-05","records":[{"metric":"steps","value":1000,"unit":"count","start_time":"2025-08-05T06:00:00.000Z","end_time":"2025-08-05T23:59:59.000Z"}]}'
   ```

2. **Run Profile 3** (Test Manual Sync) to verify Tasker → Pi communication

3. **Test weight entry** by adding weight to Samsung Health

4. **Wait for 9pm** or manually trigger Profile 1 for automated sync

## HRV Manual Entry

For HRV data, use the touchscreen form on your Pi dashboard:
- Navigate to the HRV entry component
- Enter value in milliseconds
- Form will submit to `/api/manual` endpoint
- Recent entries will be displayed

## Troubleshooting

**Common Issues**:
- **Connection refused**: Check Pi IP address (192.168.86.36) and port (8000)
- **Health Connect permission**: Ensure Tasker has health data access
- **JSON formatting**: Use exact JSON format shown above
- **Variable errors**: Check %DATE and %DATET are properly set

**Debug Steps**:
1. Check Tasker logs for HTTP response codes
2. Verify Health Connect data is available in variables
3. Test with simple curl command first
4. Check Pi server logs for incoming requests

## API Endpoints Summary

- **Automated data**: `POST /api/ingest` (steps, heart_rate)
- **Manual weight**: `POST /api/ingest` (weight in kg)
- **Manual HRV**: `POST /api/manual` (via Pi touchscreen)
- **View recent HRV**: `GET /api/manual?metric=hrv&limit=5`

Your data flow is now configured for:
✅ Daily automated sync after 9pm
✅ Weight sync trigger when added to Samsung Health  
✅ Manual HRV entry on Pi touchscreen
✅ All data formatted correctly for your database schema