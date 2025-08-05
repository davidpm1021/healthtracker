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

- **Steps & Heart Rate**: Automated via Tasker ’ Health Connect
- **Weight**: Manual Samsung Health entry ’ Tasker trigger
- **HRV**: Manual entry via Pi touchscreen

## Configuration

See `TASKER_COMPLETE_CONFIG.md` for complete Tasker setup with:
- Daily automated sync after 9pm
- Weight entry triggers
- Manual HRV entry forms

## Project Structure

- `src/`: FastAPI backend application
- `static/`: Web dashboard (HTML/CSS/JS)
- `healthtracker.db`: SQLite database
- `start_server.py`: Server startup script
- `insert_data_direct.py`: Historical data import