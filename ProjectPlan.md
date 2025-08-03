# Project Plan

## Project Overview

Build a local, touch-friendly dashboard that runs on a Raspberry Pi 5 with a 7-inch screen. It will read your Samsung Health data through Health Connect on your Android phone, then store summaries on the Pi and visualize progress in a calm, motivating way. The design keeps attention on a few core metrics, with clear weekly and monthly benchmarks and small gamified touches that reward consistency, not perfection.

**Metrics in scope:** weight, sleep, heart rate variability \[HRV from your sleep ring data], step count, trend over time.
**Data path:** Phone via Health Connect, exported on a schedule, sent over local network to the Pi, stored locally, rendered in a minimal UI.
**Design tone:** clean, high-contrast, large touch targets, simple progress bars and rings, milestone badges, gentle micro-animations only.
**Constraint:** keep it simple, no cloud backend, local storage by default.

## Technology Stack

* **Language:** Python 3.11 on the Pi for a tiny local API and scheduler, JavaScript for the browser UI
* **Framework:** FastAPI for the local API and static file serving, HTMX plus a light sprinkle of Alpine.js for interaction, Chart.js for charts
* **Database:** SQLite for summaries and goals, plus optional raw JSON dumps for imports and backups
* **Other tools:** Chromium in kiosk mode on the Pi, systemd for auto-start, Tasker on Android for the first-pass Health Connect export (upgrade path to a small Kotlin app later if needed)

> Decision note: start with Tasker + Health Connect because it is fastest to ship and avoids building an Android app. If reliability becomes problematic, add a small Kotlin companion later without changing the Pi side.

## Development Phases

### Phase 1: Foundation

**Goal:** Pi boots straight into a local dashboard shell with a working local API and an empty data model.

**Tasks**

* Hardware and OS setup, including screen rotation and touch calibration.
* Create a small FastAPI service with basic endpoints for health checks and placeholders for ingest and query.
* Define local storage layout, pick a single SQLite file for summaries and state, and a data folder for optional raw dumps.
* Configure Chromium to start in kiosk mode and load the dashboard on boot. Add a simple way to exit kiosk for maintenance.
* Build a minimal UI shell with “Today”, “Week”, “Month”, and “Goals” tabs, showing placeholder cards and progress bars.
* Document all setup steps, including networking and power settings for always-on behavior.

**Exit criteria**

* Device auto-boots to the dashboard.
* Local API responds, schema is created, placeholder UI renders at 60 fps on touch.

---

### Phase 2: Core Architecture

**Goal:** Real data arrives from the phone, gets normalized and summarized locally, and appears in the Today and Week views.

**Decisions**

* **Exporter v1:** Tasker pulls from Health Connect and posts compact JSON to the Pi every 2 hours, plus on charge and on Wi-Fi connect.
* **Security:** shared secret in an HTTP header, ingestion allowed only from your phone’s IP, LAN only.
* **Data model:** keep raw samples optional, rely on daily summaries for speed.

**Data handling**

* **Tables**

  * `raw_points` for optional raw time-series (metric, start, end, value, unit, source).
  * `daily_summaries` for per-day aggregates and last-value metrics.
  * `goals` for targets by metric and period, for example daily steps, weekly weight change.
  * `badges` for earned milestones.
  * `sync_log` for ingestion status, record counts, and windows.
* **Normalization rules**

  * Steps: sum per day.
  * Sleep: total asleep minutes per night, plus quality if available.
  * HRV: nightly rMSSD or equivalent from the ring’s sleep session, stored as milliseconds.
  * Weight: most recent value per day, kilograms internally, display in your preferred unit.
* **Scheduling**

  * Hourly job computes daily summaries from any new raw points and updates 7-day and 30-day moving averages, plus a simple trend slope for each metric.
  * Nightly job cleans and vacuums the database, and writes a timestamped local backup.

**UI rendering**

* Today view shows large cards for steps, sleep, HRV, and weight, with last sync time.
* Week view shows a simple bar chart for steps and a line chart for weight and HRV, each with a thin 7-day average overlay.

**Exit criteria**

* At least a week of real data is ingested and visible.
* Summaries match what you expect from the phone within a reasonable margin.

---

### Phase 3: Feature Implementation

**Goal:** Turn data into motivation with goals, streaks, badges, benchmarks, and gentle nudges.

**Charts and trends**

* Weight and HRV line charts with 7-day and 30-day averages and a clear up, flat, or down indicator based on slope thresholds.
* Steps bar chart for last 14 and 30 days.
* Sleep duration bar or stacked chart if sleep stages are available.

**ADHD-friendly patterns**

* Focus Mode toggle that reduces the screen to one line per metric: progress ring, goal status, and one short note.
* One accent color to indicate “on track”, neutral greys otherwise, minimal iconography.
* Subtle confetti burst when a goal is reached for the day or week.

**Goals and streaks**

* Daily goals: steps, sleep duration, HRV floor, weight logging streak.
* Weekly goals: average steps, net weight delta within a safe range.
* Streak engine counts consecutive successes, supports a “freeze” token once per month.

**Milestone badges**

* Steps: first 10k day, 7-day 8k streak, first 100k week.
* Sleep: 7 nights at or above target.
* Weight: first 1 kg toward target, 25 percent of target, goal reached.
* HRV: personal best 30-day average.
* Store badge definitions as editable JSON for easy tweaks.

**Benchmarks**

* Week over week and month over month cards that say things like “+12 percent steps vs last week” and “Avg sleep 7h12m, +18m vs last month.”

**Motivational nudges**

* Morning card: “To stay on track, aim for 7,800 steps, bedtime by 11:00 pm.”
* Early evening card: “You are 1,300 steps from today’s goal.”
* Quiet hours and a mute for the day.

**Settings**

* Edit goals, choose units, accent color, and Focus Mode default.
* Export data to CSV, import a backup, wipe local data if needed.

**Exit criteria**

* Goals can be created, edited, and achieved.
* Streaks and badges award correctly and persist.
* Benchmarks update accurately each week and month.
* Nudges appear at sensible times and can be muted.

---

### Phase 4: Polish & Production

**Goal:** Daily reliability, smooth performance, and a pleasant experience.

**Visual refinement**

* Consistent spacing and typography scale suited to a 7-inch screen.
* Color-blind-friendly palette.
* Respect system “reduce motion.”

**Performance**

* Precompute aggregates, decimate long chart ranges.
* Lazy-load history for 90-day views.

**Startup and resilience**

* Kiosk starts quickly, screen sleep controlled to your schedule.
* Graceful handling of phone offline periods with queued exports and idempotent ingestion.
* Weekly rolling backups with retention, optional encrypted USB copy.

**Testing and docs**

* Unit tests for ingestion, aggregation, and badge logic.
* Golden datasets for trend checks.
* Troubleshooting guide for exporter issues and network changes.

**Exit criteria**

* No crashes during a full week of daily use.
* Data stays consistent after reboots and network changes.
* Clear documentation for setup and recovery.

## Phase 1 Implementation Chunks

### Task 1: Hardware and OS Setup

#### Chunk 1: Raspberry Pi OS Installation and Initial Configuration (1.5 hours)

**Input Requirements:**
- Raspberry Pi 5 hardware
- MicroSD card (32GB minimum)
- Raspberry Pi Imager software
- Network connection (Ethernet preferred for initial setup)

**Output Requirements:**
- Bootable Raspberry Pi OS (64-bit, latest stable)
- SSH enabled
- User account configured
- Network connectivity established

**Files to Create/Modify:**
- `/boot/config.txt` - Initial display settings
- `/etc/hostname` - Set to "healthtracker"
- `/etc/hosts` - Update with new hostname

**Validation Steps:**
1. Pi boots successfully to desktop
2. Can SSH into Pi from development machine
3. `ping google.com` works
4. `sudo apt update` completes without errors
5. Record IP address for future access

---

#### Chunk 2: Display Driver and Touch Screen Setup (2 hours)

**Input Requirements:**
- 7-inch touchscreen connected to Pi
- Display shows desktop (even if orientation is wrong)
- SSH access to Pi

**Output Requirements:**
- Display shows correct orientation
- Touch input registers correctly
- Display resolution optimized for 7-inch screen

**Files to Create/Modify:**
- `/boot/config.txt`:
  ```
  display_rotate=1  # or 3, depending on mounting
  hdmi_group=2
  hdmi_mode=87
  hdmi_cvt=1024 600 60 6 0 0 0
  ```
- `/usr/share/X11/xorg.conf.d/40-libinput.conf` - Touch calibration

**Validation Steps:**
1. Display shows correct orientation
2. Touch test: `sudo apt install xinput && xinput list` shows touch device
3. Can tap all four corners accurately
4. Text is readable at arm's length
5. No screen tearing during window movement

---

#### Chunk 3: Touch Calibration and Input Configuration (1 hour)

**Input Requirements:**
- Display working with correct orientation
- Touch input detected but may be misaligned

**Output Requirements:**
- Touch input precisely aligned with visual elements
- Touch responsiveness optimized
- Multi-touch disabled (single touch only for simplicity)

**Files to Create/Modify:**
- `/etc/X11/xorg.conf.d/99-calibration.conf` - Touch matrix values
- Create calibration script: `/home/pi/scripts/calibrate_touch.sh`

**Validation Steps:**
1. Run `xinput_calibrator` and tap test points accurately
2. Test touch accuracy with `evtest`
3. Verify single-touch mode: rapid taps don't cause jitter
4. Test drag operations work smoothly
5. Save calibration matrix for recovery

---

#### Chunk 4: System Performance and Boot Optimization (1.5 hours)

**Input Requirements:**
- Basic OS and display working
- SSH access maintained

**Output Requirements:**
- Boot time under 30 seconds to desktop
- Unnecessary services disabled
- Power management configured for always-on display
- Swap configured appropriately

**Files to Create/Modify:**
- `/boot/cmdline.txt` - Add `quiet` for faster boot
- `/etc/systemd/system/` - Disable unnecessary services
- `/etc/lightdm/lightdm.conf` - Auto-login configuration
- `/etc/xdg/lxsession/LXDE-pi/autostart` - Disable screensaver

**Validation Steps:**
1. Time boot from power-on to desktop: < 30 seconds
2. `free -h` shows appropriate swap
3. Screen stays on for 1 hour without dimming
4. `systemctl list-unit-files --state=enabled` shows minimal services
5. CPU temperature stays under 60°C at idle

---

#### Chunk 5: Network and Security Configuration (1 hour)

**Input Requirements:**
- Pi accessible via SSH
- Network connection established

**Output Requirements:**
- Static IP configured
- Firewall rules set
- SSH key authentication only
- Hostname resolution working

**Files to Create/Modify:**
- `/etc/dhcpcd.conf` - Static IP configuration
- `/etc/ssh/sshd_config` - Disable password auth
- Install and configure `ufw` firewall rules
- `/home/pi/.ssh/authorized_keys` - Add your public key

**Validation Steps:**
1. Pi maintains same IP after reboot
2. Can SSH with key only (password fails)
3. `sudo ufw status` shows only required ports open
4. `nmap` scan from another device shows minimal exposure
5. Can ping by hostname "healthtracker.local"

---

#### Chunk 6: Recovery and Maintenance Setup (1 hour)

**Input Requirements:**
- All previous chunks completed
- System stable and accessible

**Output Requirements:**
- Backup of all configuration files
- Recovery documentation
- Maintenance scripts
- Remote access fallback

**Files to Create/Modify:**
- `/home/pi/backup/` directory with config copies
- `/home/pi/scripts/backup_config.sh` - Automated backup script
- `/home/pi/RECOVERY.md` - Step-by-step recovery guide
- Create systemd service for VNC as fallback

**Validation Steps:**
1. Config backup script runs successfully
2. Can restore from backup and maintain functionality
3. VNC connection works as SSH alternative
4. Documentation includes all customizations
5. Test full system recovery from fresh SD card

---

**Total Time: 8.5 hours (can be split across multiple days)**

## Phase 2 Implementation Chunks

### Task 1: Database and API Foundation

#### Chunk 1: Database Schema and Models (1.5 hours)

**Input Requirements:**
- Phase 1 foundation complete (basic Pi setup)
- Understanding of data model requirements from Phase 2 spec
- SQLite available on system

**Output Requirements:**
- SQLite database file created with all required tables
- Database schema matches specification exactly
- Basic database operations tested and working

**Files to Create/Modify:**
- `database/schema.sql` - Database schema definitions
- `src/models.py` - Python data models/classes for database tables
- `src/database.py` - Database connection and basic operations
- `requirements.txt` - Add SQLite dependencies if needed

**Validation Steps:**
1. Database file creates successfully with `sqlite3 healthtracker.db < database/schema.sql`
2. All 5 tables exist: `raw_points`, `daily_summaries`, `goals`, `badges`, `sync_log`
3. Can insert and query test data for each table
4. Python models can connect to database without errors
5. Basic CRUD operations work for each table

---

#### Chunk 2: FastAPI Foundation and Health Check (1 hour)

**Input Requirements:**
- Database schema and models completed
- Basic understanding of FastAPI framework

**Output Requirements:**
- FastAPI application starts and responds
- Health check endpoint working
- Basic project structure established
- Static file serving configured

**Files to Create/Modify:**
- `src/main.py` - FastAPI application entry point
- `src/api/__init__.py` - API module initialization
- `src/api/health.py` - Health check endpoints
- `requirements.txt` - Add FastAPI, uvicorn dependencies
- `static/` directory - For serving UI files

**Validation Steps:**
1. `uvicorn src.main:app --reload` starts without errors
2. `GET /health` returns 200 status with basic system info
3. `GET /api/health/db` confirms database connectivity
4. Static files serve correctly from `/static/` path
5. API responds within 100ms for health checks

---

#### Chunk 3: Data Ingestion API with Security (2 hours)

**Input Requirements:**
- FastAPI foundation working
- Database models available
- Understanding of security requirements (shared secret, IP filtering)

**Output Requirements:**
- Secure ingestion endpoint accepts JSON health data
- IP filtering and authentication working
- Raw data stored in database correctly
- Error handling and validation in place

**Files to Create/Modify:**
- `src/api/ingest.py` - Data ingestion endpoints
- `src/auth.py` - Authentication and IP filtering middleware
- `src/validators.py` - Data validation schemas
- `config.py` - Configuration management for secrets and allowed IPs
- `.env.example` - Environment variable template

**Validation Steps:**
1. `POST /api/ingest` accepts valid JSON with correct auth header
2. Request with wrong IP or missing auth header returns 403
3. Invalid data format returns 400 with clear error message
4. Valid health data appears in `raw_points` table
5. Concurrent requests handle gracefully without data corruption

---

### Task 2: Data Processing

#### Chunk 4: Data Normalization Engine (1.5 hours)

**Input Requirements:**
- Raw data ingestion working
- Understanding of normalization rules for each metric type
- Database contains some test raw data

**Output Requirements:**
- Normalization functions for steps, sleep, HRV, weight
- Raw data correctly transformed into daily summaries
- Edge cases handled (missing data, duplicates, invalid values)

**Files to Create/Modify:**
- `src/normalization.py` - Core normalization functions
- `src/metrics/__init__.py` - Metrics processing module
- `src/metrics/steps.py` - Steps-specific logic (sum per day)
- `src/metrics/sleep.py` - Sleep processing (total minutes, quality)
- `src/metrics/hrv.py` - HRV processing (nightly rMSSD)
- `src/metrics/weight.py` - Weight processing (most recent per day)

**Validation Steps:**
1. Steps raw data sums correctly into daily totals
2. Sleep data aggregates into nightly totals with quality scores
3. HRV data extracts nightly values correctly
4. Weight data selects most recent value per day
5. Duplicate data doesn't create multiple summaries for same day

---

#### Chunk 5: Daily Summary Computation (1 hour)

**Input Requirements:**
- Normalization engine completed
- Raw data available in database
- Understanding of summary table structure

**Output Requirements:**
- Automated daily summary generation
- Moving averages calculated (7-day, 30-day)
- Trend slopes computed for each metric

**Files to Create/Modify:**
- `src/summaries.py` - Daily summary computation
- `src/trends.py` - Moving average and trend calculation
- `src/api/summaries.py` - API endpoints for summary data

**Validation Steps:**
1. Daily summaries generate correctly from raw data
2. 7-day and 30-day moving averages calculate accurately
3. Trend slopes indicate up/flat/down correctly
4. Summary API returns data in expected format
5. Performance: summary generation completes in <5 seconds for 30 days of data

---

#### Chunk 6: Background Job Scheduler (1.5 hours)

**Input Requirements:**
- Summary computation working
- Understanding of scheduling requirements (hourly, nightly jobs)

**Output Requirements:**
- Hourly job for summary updates running
- Nightly job for database maintenance
- Job status tracking and error handling
- Configurable job intervals

**Files to Create/Modify:**
- `src/scheduler.py` - Background job management
- `src/jobs/__init__.py` - Jobs module
- `src/jobs/hourly.py` - Hourly summary updates
- `src/jobs/nightly.py` - Database cleanup and backup
- `src/api/jobs.py` - Job status API endpoints

**Validation Steps:**
1. Hourly job runs automatically and updates summaries
2. Nightly job performs database VACUUM and creates backup
3. Job failures log errors but don't crash the system
4. Job status API shows last run times and success/failure
5. Jobs can be manually triggered via API for testing

---

### Task 3: User Interface

#### Chunk 7: Basic UI Framework (2 hours)

**Input Requirements:**
- FastAPI serving static files
- API endpoints returning data
- Understanding of UI requirements (Today/Week views)

**Output Requirements:**
- HTML structure for dashboard with tabs
- HTMX integration for dynamic content
- Basic styling for touch-friendly interface
- Data loading from API working

**Files to Create/Modify:**
- `static/index.html` - Main dashboard HTML
- `static/css/styles.css` - Basic styling for 7-inch screen
- `static/js/dashboard.js` - Alpine.js setup and interactions
- `static/components/` - Reusable UI components
- `src/api/ui.py` - UI data endpoints

**Validation Steps:**
1. Dashboard loads at root URL with tab navigation
2. Today tab shows placeholder cards for each metric
3. Week tab shows empty chart containers
4. Touch interactions work smoothly (tap, swipe)
5. Data loads from API and populates cards correctly

---

#### Chunk 8: Today View Implementation (1.5 hours)

**Input Requirements:**
- UI framework established
- Summary data API working
- Understanding of Today view requirements

**Output Requirements:**
- Large metric cards displaying current data
- Last sync timestamp shown
- Visual indicators for data freshness
- Touch-optimized layout

**Files to Create/Modify:**
- `static/components/metric-card.html` - Metric card component
- `static/components/today-view.html` - Today view layout
- `static/css/today.css` - Today view specific styles
- `static/js/today.js` - Today view interactions

**Validation Steps:**
1. Today view displays current steps, sleep, HRV, and weight
2. Cards show large, readable numbers appropriate for 7-inch screen
3. Last sync time displays and updates correctly
4. Cards indicate data staleness with visual cues
5. Touch interactions provide appropriate feedback

---

#### Chunk 9: Week View with Charts (2 hours)

**Input Requirements:**
- Today view working
- Chart.js available
- Weekly summary data from API

**Output Requirements:**
- Bar chart for steps over 7 days
- Line charts for weight and HRV with moving averages
- Charts optimized for touch interaction
- Responsive design for 7-inch screen

**Files to Create/Modify:**
- `static/components/week-view.html` - Week view layout
- `static/js/charts.js` - Chart.js configuration and setup
- `static/css/charts.css` - Chart styling
- `src/api/charts.py` - Chart data endpoints

**Validation Steps:**
1. Steps bar chart displays last 7 days correctly
2. Weight line chart shows data points with 7-day average overlay
3. HRV line chart displays with trend indicators
4. Charts are touch-responsive and readable on 7-inch screen
5. Chart data updates when new summaries are computed

---

**Total Phase 2 Time: 13.5 hours**

## Current Status

* **Current Phase:** Phase 2 - Core Architecture
* **Current Sub-Component:** Database and API Foundation
* **Current Chunk:** Chunk 1 - Database Schema and Models
* **Approval Status:** Phase 2 breakdown approved

## Approval Gates

* [x] Phase 1 breakdown approved
* [x] Phase 2 breakdown approved
* [ ] Phase 3 breakdown approved
* [ ] Phase 4 breakdown approved

## Implementation Log

* **Chunk 1 - Raspberry Pi OS Installation and Initial Configuration**: Completed
  - Raspberry Pi OS installed and configured
  - SSH enabled and network connectivity established
  - Hostname set to "healthtracker"

* **Chunk 2 - Display Driver and Touch Screen Setup**: PENDING
  - NOTE: To be completed when physically at Pi device

* **Chunk 3 - Touch Calibration and Input Configuration**: PENDING
  - NOTE: To be completed when physically at Pi device

* **Chunk 4 - System Performance and Boot Optimization**: Completed
  - Boot time optimized to under 30 seconds
  - Unnecessary services disabled
  - Power management configured for always-on display
  - Swap configured appropriately

* **Chunk 5 - Network and Security Configuration**: Completed
  - Static IP configured
  - Firewall rules set
  - SSH key authentication only
  - Hostname resolution working

* **Chunk 6 - Recovery and Maintenance Setup**: Completed
  - Backup of all configuration files
  - Recovery documentation created
  - Maintenance scripts prepared
  - Remote access fallback configured

