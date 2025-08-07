# MVP Cleanup Summary

## What Was Removed/Archived

### Removed Duplicate Server Files
- ❌ `mvp_server.py` - Deleted (duplicate functionality)
- ❌ `start_simple_server.py` - Deleted (incomplete server)
- ❌ `SWITCH_TO_FULL_SERVER.md` - Deleted (no longer needed)

### Archived Non-MVP Features to `archive_non_mvp/`
- 📦 Goals system (`goals.py`, `goals_service.py`)
- 📦 Progress tracking (`progress.py`, `progress_tracker.py`)
- 📦 Badges system (`badges.py`, `badges_service.py`)
- 📦 Background jobs (`jobs.py`, `scheduler.py`, `jobs/` directory)
- 📦 Advanced services (`services/` directory)

## What Remains (MVP Only)

### Single Server
- ✅ `start_server.py` - One server startup script
- ✅ `src/main.py` - Clean MVP server with only essential features

### Essential API Endpoints
- ✅ `/api/ingest` - Receives data from Tasker
- ✅ `/api/manual` - HRV manual entry
- ✅ `/api/ui/*` - Dashboard views
- ✅ `/api/charts` - Data visualization
- ✅ `/api/health` - Health checks

### Core Features
- ✅ Data ingestion from phone
- ✅ Dashboard visualization
- ✅ Manual HRV entry
- ✅ Historical data import
- ✅ Charts and trends

## Benefits of This Cleanup

1. **No Confusion**: Only one server file to run
2. **Simpler Deployment**: Less files to manage
3. **Easier Maintenance**: Clear MVP scope
4. **Faster Performance**: No unnecessary features loading
5. **Clean Codebase**: Archived features can be restored later if needed

## How to Use

Just run one command on the Pi:
```bash
python3 start_server.py
```

That's it! No need to remember which server has which features.