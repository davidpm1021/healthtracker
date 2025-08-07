# HealthTracker

A minimal health metrics dashboard for personal use, designed to run on a Raspberry Pi with touchscreen.

## Quick Start

1. **Start the server**:
   ```bash
   python3 start_server.py
   ```

2. **Access dashboard**: http://localhost:8000/static/index.html

3. **Import your historical data**:
   ```bash
   python3 insert_data_direct.py
   ```

## Features

- **Today & Week Views**: Essential health metrics display
- **Automated Data Sync**: Tasker + Health Connect integration
- **Manual HRV Entry**: Touch-friendly Pi interface
- **Data Visualization**: Charts for weight, heart rate, steps, HRV

## Data Sources

- **Steps & Heart Rate**: Automated via Tasker � Health Connect
- **Weight**: Manual Samsung Health entry � Tasker trigger
- **HRV**: Manual entry via Pi touchscreen

## Configuration

See `TASKER_COMPLETE_CONFIG.md` for complete Tasker setup with:
- Daily automated sync after 9pm
- Weight entry triggers
- Manual HRV entry forms

## Project Structure

- `src/`: FastAPI backend application (MVP only)
- `static/`: Web dashboard (HTML/CSS/JS)
- `healthtracker.db`: SQLite database
- `start_server.py`: Single server startup script
- `insert_data_direct.py`: Historical data import
- `test_ingestion.sh`: Test data ingestion endpoint
- `deploy_and_restart.sh`: Deploy updates to Pi
- `archive_non_mvp/`: Archived features for future use

## Troubleshooting

### Server Issues

**Server not running**:
```bash
# SSH to Pi and start server
ssh davidpm@192.168.86.36
cd /home/davidpm/healthtracker
pkill python3  # Kill any existing server
python3 start_server.py  # Start the server
```

**Test if ingestion is working**:
```bash
# From your local machine
bash test_ingestion.sh

# Or test specific endpoint
curl http://192.168.86.36:8000/api/ingest/test
```

### Tasker Setup Issues

**Connection refused from Tasker**:
- Ensure Pi IP is correct: `192.168.86.36`
- Check server is running: `ssh davidpm@192.168.86.36 'ps aux | grep python'`
- Verify port 8000 is open: `ssh davidpm@192.168.86.36 'netstat -tlnp | grep 8000'`

**JSON format errors**:
- API accepts both `"records"` and `"data_points"` arrays
- Use test script to verify format: `bash test_ingestion.sh`
- Check server logs: `ssh davidpm@192.168.86.36 'tail -f /home/davidpm/healthtracker/server.log'`

**Variables not working**:
- Ensure `%DATE` is set to `%DATY-%DATM-%DATD`
- Test with hardcoded values first
- Use Tasker's "Flash" action to debug variable values

### Data Not Showing in Dashboard

**Check database**:
```bash
ssh davidpm@192.168.86.36
sqlite3 /home/davidpm/healthtracker/healthtracker.db
.tables
SELECT COUNT(*) FROM raw_points;
SELECT * FROM raw_points ORDER BY created_at DESC LIMIT 5;
```

**Verify summaries are computed**:
```bash
# Trigger manual summary computation
curl -X POST http://192.168.86.36:8000/api/compute
```

### Quick Fixes

**Deploy and restart everything**:
```bash
bash deploy_and_restart.sh
```

**Reset to known good state**:
```bash
ssh davidpm@192.168.86.36
cd /home/davidpm/healthtracker
git pull
python3 start_server.py
```

## Support

For issues, check:
1. Server logs: `/home/davidpm/healthtracker/server.log`
2. Database integrity: `sqlite3 healthtracker.db "PRAGMA integrity_check;"`
3. API documentation: http://192.168.86.36:8000/docs