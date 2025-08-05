# How to Run HealthTracker Dashboard

## Quick Start

1. **Start the server** (in one terminal):
   ```bash
   cd /mnt/c/Users/Dave/Cursor/HealthTracker
   python3 run_server.py
   ```

2. **Access the dashboard** (in your browser):
   - Open: http://localhost:8000/static/index.html
   - API docs: http://localhost:8000/docs

3. **Trigger data processing** (in another terminal):
   ```bash
   curl -X POST http://localhost:8000/api/compute
   ```

## What You'll See

After starting the server and triggering data processing, the dashboard will show:
- **Today View**: Current metrics with large touch-friendly cards
- **Week View**: Charts showing trends (once implemented)
- **Manual Entry**: Cards for HRV, mood, and energy input
- **Sync Status**: Shows last data update time

## Mock Data Available

The database already contains 30 days of realistic mock data:
- Steps: Daily activity patterns (lower on weekends)
- Sleep: Nightly duration with quality metrics
- Weight: Gradual trend with natural fluctuations
- Heart Rate: Resting and activity readings
- Manual Entries: HRV, mood, and energy ratings

## Troubleshooting

If the server doesn't start:
1. Make sure you're in the project root directory
2. Check that port 8000 is not already in use
3. Look for error messages in the terminal

If you see import errors:
- The project uses relative imports that require running from the project root
- Always use `python3 run_server.py` instead of running main.py directly

## Development Tips

- The server auto-reloads when you change code (when using run_local.sh)
- Mock data can be regenerated with: `python3 scripts/generate_mock_data.py`
- Database is stored in: `healthtracker.db`