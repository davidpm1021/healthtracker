# Project Plan

## Project Overview

Build a local, touch-friendly dashboard that runs on a Raspberry Pi 5 with a 7-inch screen. It will read your Samsung Health data through Health Connect on your Android phone, then store summaries on the Pi and visualize progress in a calm, motivating way. The design keeps attention on a few core metrics, with clear weekly and monthly benchmarks and small gamified touches that reward consistency, not perfection.

**Metrics in scope:** weight, sleep, heart rate, step count, plus manual entry for HRV and subjective metrics, trend over time.
**Data path:** Phone via Health Connect for automated metrics (steps, sleep, weight, heart rate), manual entry UI for HRV and subjective data, all stored locally, rendered in a minimal UI.
**Design tone:** clean, high-contrast, large touch targets, simple progress bars and rings, milestone badges, gentle micro-animations only.
**Constraint:** keep it simple, no cloud backend, local storage by default.

## AI-Assisted Development Workflow

### 🎯 Core Methodology
This project uses a structured, phase-based development approach with AI (Claude Code) as an implementation partner while maintaining human control over architecture and decisions.

### 📋 Planning Structure

1. **Mind Dump → Structure Pipeline**
   - Start: Raw brain dump of project idea
   - Process: Use prompts to convert into structured project plan
   - Output: Organized phases with clear objectives

2. **Three-Tier Breakdown System**
   - **Tier 1**: Development Phases (Strategic - Foundation, Architecture, Features, Polish)
   - **Tier 2**: Sub-components (Tactical - logical chunks within phases)
   - **Tier 3**: Implementation Chunks (Tasks - 1-2 hour coding tasks)

3. **ProjectPlan.md as Single Source of Truth**
   - Contains complete project structure
   - Tracks current status and progress
   - Gets updated as requirements evolve
   - Referenced by AI for all implementation work

### 🤖 AI Interaction Patterns

**Chunking Prompts (Planning Phase)**
- "Looking at this project plan, break down [PHASE NAME] into logical sub-components..."
- "Take this sub-component and break it into 1-2 hour implementation chunks..."

**Implementation Prompts (Execution Phase)**
- "Looking at ProjectPlan.md, implement the current chunk listed under 'Current Chunk'. Only create/modify files explicitly listed. Don't touch ProjectPlan.md or other files."

**Status Management Prompts**
- "Update the 'Current Chunk' to the next chunk in sequence. Only modify Current Status section."

### 🔧 File Management Strategy

**What AI Can Touch**
- Implementation files: Source code, configs, requirements
- Specific scope: Only files listed in current chunk
- Validation: Must complete chunk requirements before moving on

**What AI Cannot Touch**
- ProjectPlan.md: Human maintains this
- Files outside current chunk: Strict boundaries
- Architecture decisions: Human approves major changes

**When to Alter Files**
- AI implements: Current chunk requirements only
- Human updates: ProjectPlan.md status, architectural changes
- Human approves: All chunk completions before progression

### 🚦 Quality Control Gates

**Chunk-Level Gates**
- All validation steps must pass
- Human explicitly approves completion
- Status updated in ProjectPlan.md before next chunk

**Phase-Level Gates**
- All chunks in phase complete
- System tested end-to-end
- Architecture review before next phase

### 💬 AI Prompt Principles

**Scope Limitation (Critical)**
- Hyper-specific tasks: "Only implement the User model, nothing else"
- Boundary setting: "Don't touch files X, Y, Z"
- Single responsibility: One clear objective per chunk

**Context Provision**
- Reference ProjectPlan.md: AI always knows current context
- Chunk requirements: Clear input/output specifications
- Dependencies: What must exist before chunk starts

**Human Oversight**
- Approval gates: Human decides when to move forward
- Architecture control: AI suggests, human decides
- Scope creep prevention: Strict chunk boundaries

### 🔄 Iteration Process

1. Plan phases (human-driven with AI assistance)
2. Chunk current phase (AI breaks down, human approves)
3. Implement chunk (AI executes, human validates)
4. Update status (human moves to next chunk)
5. Repeat until phase complete

### 🎪 Key Success Factors

- **Small chunks**: 1-2 hours max, easily validated
- **Clear boundaries**: AI knows exactly what it can/cannot touch
- **Human control**: Architecture and progression decisions stay human
- **Single source of truth**: ProjectPlan.md keeps everyone aligned
- **Validation-driven**: Every chunk must prove it works before progression

*This approach treats AI as a very capable junior developer with strict supervision and clear task boundaries.*

## Technology Stack

* **Language:** Python 3.11 on the Pi for a tiny local API and scheduler, JavaScript for the browser UI
* **Framework:** FastAPI for the local API and static file serving, HTMX plus a light sprinkle of Alpine.js for interaction, Chart.js for charts
* **Database:** SQLite for summaries and goals, plus optional raw JSON dumps for imports and backups
* **Other tools:** Chromium in kiosk mode on the Pi, systemd for auto-start, Tasker on Android for the first-pass Health Connect export (upgrade path to a small Kotlin app later if needed)

> Decision note: start with Tasker + Health Connect because it is fastest to ship and avoids building an Android app. If reliability becomes problematic, add a small Kotlin companion later without changing the Pi side.

## Architectural Decisions

### Data Model Changes (Implemented in Phase 2 Chunk 4)

**Decision**: Separate automated metrics from manual entry metrics

**Rationale**: 
- HRV data from wearables is often inconsistent and requires user validation
- Subjective metrics (mood, energy) inherently require manual input
- Automated processing should focus on reliable, high-frequency data streams
- Manual entries allow for richer context (notes, qualitative observations)

**Implementation**:
- **Automated metrics**: steps, sleep, weight, heart_rate → processed via normalization engine
- **Manual metrics**: hrv, mood, energy, notes → stored directly via manual entry API
- Separate database tables and validation schemas
- Migration script preserves existing HRV data

**Impact**:
- Cleaner separation of concerns
- Better data quality for automated summaries
- Enhanced user control over subjective data
- Simplified normalization logic

---

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

  * `raw_points` for optional raw time-series (steps, sleep, weight, heart_rate - automated metrics only).
  * `daily_summaries` for per-day aggregates and last-value metrics (automated metrics only).
  * `manual_entries` for user-input data (HRV, mood, energy, notes, etc.).
  * `goals` for targets by metric and period, supporting both automated and manual metrics.
  * `badges` for earned milestones.
  * `sync_log` for ingestion status, record counts, and windows.
* **Normalization rules** (automated metrics only)

  * Steps: sum per day.
  * Sleep: total asleep minutes per night, plus quality if available.
  * Weight: most recent value per day, kilograms internally, display in your preferred unit.
  * Heart Rate: average or spot readings per day (implementation pending).
  
* **Manual entry handling**

  * HRV: User-input nightly rMSSD values in milliseconds, stored directly without normalization.
  * Mood/Energy: User-input scores (1-10 scale) with optional text descriptions.
  * Notes: Text-only entries for qualitative observations.
* **Scheduling**

  * Hourly job computes daily summaries from any new raw points and updates 7-day and 30-day moving averages, plus a simple trend slope for each metric.
  * Nightly job cleans and vacuums the database, and writes a timestamped local backup.

**UI rendering**

* Today view shows large cards for steps, sleep, heart rate, and weight (automated), plus HRV and mood (manual), with last sync time.
* Week view shows bar charts for steps and line charts for weight and heart rate (automated), plus HRV trends from manual entries.
* Manual entry interface allows quick input of HRV, mood, energy, and notes with date selection and validation.

**Exit criteria**

* At least a week of real data is ingested and visible.
* Summaries match what you expect from the phone within a reasonable margin.

---

### Phase 3: Feature Implementation

**Goal:** Turn data into motivation with goals, streaks, badges, benchmarks, and gentle nudges.

**Charts and trends**

* Weight and heart rate line charts with 7-day and 30-day averages and a clear up, flat, or down indicator based on slope thresholds.
* HRV line charts from manual entries with trend indicators (no automated averaging due to sparse manual data).
* Steps bar chart for last 14 and 30 days.
* Sleep duration bar or stacked chart if sleep stages are available.

**ADHD-friendly patterns**

* Focus Mode toggle that reduces the screen to one line per metric: progress ring, goal status, and one short note.
* One accent color to indicate “on track”, neutral greys otherwise, minimal iconography.
* Subtle confetti burst when a goal is reached for the day or week.

**Goals and streaks**

* Daily goals: steps, sleep duration, heart rate zone, weight logging streak, HRV entry streak (manual).
* Weekly goals: average steps, net weight delta within a safe range, HRV consistency (manual entries).
* Streak engine counts consecutive successes, supports a "freeze" token once per month.

**Milestone badges**

* Steps: first 10k day, 7-day 8k streak, first 100k week.
* Sleep: 7 nights at or above target.
* Weight: first 1 kg toward target, 25 percent of target, goal reached.
* Heart Rate: resting HR improvement, target zone consistency.
* HRV: personal best reading, 7-day entry streak, monthly consistency (manual entries).
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

**Goal:** Daily reliability, smooth performance, and live data integration from phone.

**Tasker/Health Connect Integration**

* Configure Tasker HTTP Request with proper authentication headers
* Set up automated Health Connect data export every 2 hours
* Configure triggers: on charge, on Wi-Fi connect, scheduled intervals
* Test and validate Phone → Pi → Dashboard data pipeline
* Create fallback mechanisms for network issues
* Document Tasker setup process for reproducibility

**Visual refinement**

* Consistent spacing and typography scale suited to a 7-inch screen.
* Color-blind-friendly palette.
* Respect system "reduce motion."

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
* Complete Tasker configuration documentation

**Exit criteria**

* Live data flowing from phone to dashboard reliably
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
2. All 6 tables exist: `raw_points`, `daily_summaries`, `manual_entries`, `goals`, `badges`, `sync_log`
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
- Normalization functions for steps, sleep, weight, heart rate (automated metrics only)
- Raw data correctly transformed into daily summaries
- Edge cases handled (missing data, duplicates, invalid values)
- HRV removed from automated processing (handled via manual entries)

**Files to Create/Modify:**
- `src/normalization.py` - Core normalization functions
- `src/metrics/__init__.py` - Metrics processing module
- `src/metrics/steps.py` - Steps-specific logic (sum per day)
- `src/metrics/sleep.py` - Sleep processing (total minutes, quality)
- `src/metrics/weight.py` - Weight processing (most recent per day)
- `src/api/manual.py` - Manual entry API for HRV and subjective metrics

**Validation Steps:**
1. Steps raw data sums correctly into daily totals
2. Sleep data aggregates into nightly totals with quality scores
3. Weight data selects most recent value per day
4. Manual entry API accepts HRV, mood, energy, and notes
5. Duplicate data doesn't create multiple summaries for same day
6. Heart rate normalization framework ready for implementation

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
1. Today view displays current steps, sleep, heart rate, and weight (automated)
2. Manual entry cards show HRV and mood with input options  
3. Cards show large, readable numbers appropriate for 7-inch screen
4. Last sync time displays and updates correctly
5. Cards indicate data staleness with visual cues
6. Touch interactions provide appropriate feedback

---

#### Chunk 9: Week View with Charts (2 hours)

**Input Requirements:**
- Today view working
- Chart.js available
- Weekly summary data from API

**Output Requirements:**
- Bar chart for steps over 7 days
- Line charts for weight and heart rate with moving averages
- Separate chart for manual HRV entries (no averaging due to sparse data)
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
3. Heart rate line chart displays with trend indicators
4. HRV manual entry chart shows individual data points
5. Charts are touch-responsive and readable on 7-inch screen
6. Chart data updates when new summaries are computed

---

**Total Phase 2 Time: 13.5 hours**

## Current Status

* **Current Phase:** MVP COMPLETE - Ready for Production Use
* **Current Sub-Component:** Data Integration and User Testing
* **Current Chunk:** Real data import and Tasker configuration
* **Next Chunk:** User acceptance testing and deployment validation
* **Approval Status:** Phase 2 COMPLETED, MVP SIMPLIFIED AND DEPLOYED
* **Deployment Status:** ✅ Repository deployed to https://github.com/davidpm1021/healthtracker
* **Data Status:** ✅ Historical data imported, ready for live Tasker sync

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

* **Phase 2 Chunk 1 - Database Schema and Models**: Completed
  - SQLite database created with all required tables
  - Python data models implemented
  - Database connection and CRUD operations working
  - All validation tests passed

* **Phase 2 Chunk 2 - FastAPI Foundation and Health Check**: Completed
  - FastAPI application created with CORS middleware
  - Health check endpoints implemented (/health, /api/health/db, /api/health/storage)
  - Static file serving configured
  - API module structure established
  - All validation tests passed

* **Phase 2 Chunk 3 - Data Ingestion API with Security**: Completed
  - Secure ingestion endpoint (POST /api/ingest) with authentication
  - IP filtering and shared secret authentication implemented
  - Data validation schemas with Pydantic (HealthDataBatch, HealthDataPoint)
  - Configuration management with environment variables (.env.example)
  - Error handling, logging, and comprehensive security features
  - All validation tests passed

* **Phase 2 Chunk 4 - Data Normalization Engine**: Completed (**MAJOR ARCHITECTURAL CHANGES**)
  - **BREAKING CHANGE**: HRV removed from automated processing, moved to manual entry system
  - Core normalization functions (src/normalization.py) updated for automated metrics only
  - Metrics processing module structure (src/metrics/) with base MetricProcessor class
  - Steps-specific logic (src/metrics/steps.py) - sums step counts per day
  - Sleep processing (src/metrics/sleep.py) - aggregates total minutes per night with quality
  - Weight processing (src/metrics/weight.py) - selects most recent measurement per day with body composition
  - **NEW**: Heart rate support framework added (implementation pending)
  - **NEW**: Manual entry API (src/api/manual.py) - handles HRV, mood, energy, notes
  - **NEW**: Database schema updated - added manual_entries table, migration script created
  - **NEW**: Separate validation schemas for automated vs manual metrics
  - Comprehensive validation testing updated - 9 individual processor tests passed, full normalization test passed

## Major Architecture Changes Summary

**Phase 2 Chunk 4 introduced breaking changes that significantly improved the system architecture:**

### Database Schema Changes
- **Added**: `manual_entries` table for user-input data (HRV, mood, energy, notes)
- **Updated**: `raw_points` and `daily_summaries` now handle only automated metrics
- **Migration**: Created `database/migrate_remove_hrv.sql` to preserve existing HRV data
- **Models**: Added `ManualEntry` model and `ManualMetricType` constants

### API Endpoints Changes  
- **Added**: `/api/manual` - Manual data entry endpoint with full CRUD operations
- **Added**: `/api/manual/batch` - Batch manual entry processing
- **Updated**: `/api/ingest` - Now validates only automated metrics (steps, sleep, weight, heart_rate)
- **Removed**: HRV from automated ingestion validation

### Data Processing Changes
- **Removed**: HRV normalization from automated processing pipeline
- **Added**: Heart rate support framework (validation and unit conversion ready)
- **Updated**: Normalization engine processes only automated metrics
- **Preserved**: All existing normalization logic for steps, sleep, weight

### User Interface Impact (Future Phases)
- **Today View**: Will show automated metrics + manual entry cards for HRV/mood
- **Week View**: Separate charts for automated trends vs manual entry points
- **Manual Entry UI**: New interface for quick HRV, mood, energy, notes input

### Benefits Achieved
1. **Cleaner Architecture**: Clear separation between automated and manual data
2. **Better Data Quality**: Automated summaries use only reliable, consistent data
3. **Enhanced User Control**: Full control over subjective and variable metrics
4. **Improved Scalability**: Easy to add new manual metrics without touching normalization
5. **Preserved Data**: All existing HRV data migrated safely to manual entries

**Current Status**: System successfully handles mixed automated/manual metrics with comprehensive validation and testing.

* **Phase 2 Chunk 5 - Daily Summary Computation**: Completed
  - Daily summary computation engine (src/summaries.py) - SummaryComputer class with automatic date range processing
  - Moving averages calculation (7-day, 30-day) with window-based processing
  - Trend slope calculation using linear regression for metric trend analysis
  - Summary API endpoints (src/api/summaries.py) - GET /api/summaries/{metric}, GET /api/summaries, GET /api/trends/{metric}
  - Advanced trend analysis utilities (src/trends.py) - TrendAnalyzer class with comprehensive analysis functions
  - **Performance validated**: Summary generation completes in <5 seconds for 30 days of data (4.12s measured)
  - **Quality validated**: All test cases passed - computation, moving averages, trend analysis, comprehensive analysis
  - API integration completed - compute summaries (POST /api/compute), update analytics (POST /api/update-analytics)

* **Phase 2 Chunk 6 - Background Job Scheduler**: Completed
  - Background job management system (src/scheduler.py) - JobScheduler class with threading and configurable intervals
  - Hourly jobs implementation (src/jobs/hourly.py) - 3 jobs: summary computation, trend analysis, data quality checks
  - Nightly jobs implementation (src/jobs/nightly.py) - 4 jobs: database maintenance, backups, cleanup, health reports
  - Job status tracking and error handling - comprehensive JobResult and JobDefinition classes with failure recovery
  - Job status API endpoints (src/api/jobs.py) - GET /api/jobs/status, GET /api/jobs, POST /api/jobs/{name}/run
  - **Validation completed**: All 5 test categories passed - basic functionality, threading, error handling, job registration, database execution
  - **Integration completed**: Scheduler auto-starts with FastAPI application, graceful shutdown on app termination
  - **Job intervals configured**: Hourly (60m), Data quality (120m), Nightly maintenance (1440m/24h)

* **Phase 2 Chunk 7 - Basic UI Framework**: Completed
  - HTML dashboard structure (static/index.html) - 4-tab navigation with Today/Week/Month/Goals views optimized for 7-inch touchscreen
  - Touch-friendly CSS styling (static/css/styles.css) - 15KB comprehensive stylesheet with responsive design, 44px minimum touch targets
  - Alpine.js interactive components (static/js/dashboard.js) - Complete dashboard functionality with tab switching, modal management, and touch gestures
  - HTMX dynamic content loading - Automatic data refresh every 30-300s with innerHTML swapping and error handling
  - UI data endpoints (src/api/ui.py) - 5 endpoints generating HTML fragments for today/week/month/goals/manual-entry-forms
  - **Touch optimization**: Swipe gestures for tab navigation, haptic feedback, large touch targets, optimized for 1024x600 and 800x480 screens
  - **Accessibility features**: High contrast design, clear typography with proper line-height, ARIA-friendly structure
  - **Framework integration**: Chart.js for data visualization, external CDN loading for Alpine.js/HTMX with local fallbacks
  - **Validation completed**: All 5 test categories passed - static files, endpoints, data generation, responsive design, JavaScript functionality

* **Phase 2 Chunk 8 - Today View Implementation**: Completed
  - **Component architecture**: today-view.html and metric-card.html template system with variable replacement
  - **New API endpoints**: /api/ui/today/primary, /secondary, /stats, /manual-status, /insights for modular data loading
  - **Enhanced metric cards**: Data freshness indicators (fresh/stale/missing), trend arrows, 7-day comparisons, action buttons
  - **Sync status banner**: Real-time online/offline detection, last sync timestamps, manual refresh functionality
  - **Quick stats summary**: Total metrics, completed goals, streak days, health score with auto-updates every 5 minutes
  - **Manual entry section**: Touch-optimized cards for HRV, Mood, Energy, Notes with real-time status tracking
  - **Today's insights**: Personalized recommendations based on steps, sleep, and manual entry patterns
  - **Alpine.js integration**: Reactive data stores (todayStats, manualEntryStatus) with automatic periodic updates
  - **Touch optimization**: 44px minimum targets, backdrop blur effects, responsive grids for 1024x600/800x480 screens
  - **Accessibility**: Semantic HTML, proper color contrast, readable typography, keyboard navigation support
  - **Validation completed**: All 6 test categories passed - component templates, API endpoints, JavaScript integration, data flow, responsive design, accessibility

## Phase 2 - DEPLOYMENT & INTEGRATION STATUS

* **GitHub Repository**: ✅ Successfully deployed to https://github.com/davidpm1021/healthtracker
* **Pi Hardware Setup**: ✅ Complete (Pi 5, 7-inch screen, SSH access, static IP: 192.168.86.36)
* **FastAPI Server**: ✅ Running on Pi at http://192.168.86.36:8000
* **Database**: ✅ SQLite operational with all 6 tables
* **Background Jobs**: ✅ Scheduler running (hourly summaries, nightly maintenance)
* **Dashboard UI**: ✅ Available at http://192.168.86.36:8000/static/index.html

## Current Development Status

**Phase 2 Complete**: Core architecture fully implemented with mock data support
**Phase 3 Ready**: Can now proceed with feature implementation using mock data
**Tasker Integration**: Deferred to Phase 4 - Polish & Production

**Mock Data Available:**
- 30 days of realistic health metrics
- Automated: steps, sleep, weight, heart rate
- Manual: HRV, mood, energy entries
- Run `python scripts/generate_mock_data.py` to populate database

**Next Steps:**
1. Generate mock data and verify dashboard display
2. Begin Phase 3: Week View with Charts implementation
3. Implement goals, streaks, badges, and motivational features
4. Phase 4 will include Tasker/Health Connect integration

## Phase 3 - FEATURE IMPLEMENTATION STATUS

### Completed Components ✅

* **Phase 3 Chunk 9 - Week View with Charts**: Completed
  - Full week view component (static/components/week-view.html)
  - Complete Chart.js integration (static/js/charts.js)
  - Individual chart modules for steps, weight, heart rate, HRV, sleep
  - Touch-optimized responsive design for 7-inch screen
  - Chart data API endpoints implemented

* **Goals System**: Completed
  - Complete REST API (src/api/goals.py) with full CRUD operations
  - Goals service layer with business logic (src/services/goals_service.py)
  - Goal models with types, frequencies, and statuses (src/models/goals.py)
  - Goals UI pages and JavaScript (static/goals.html, static/js/goals.js)
  - Goal achievement tracking and progress calculation

* **Streaks Engine**: Completed
  - Streak calculation engine (src/services/streak_engine.py)
  - Freeze token system (src/services/freeze_tokens.py) - one per month
  - Streak display components (static/js/components/streak-*.js)
  - Integration with goals for consecutive success tracking

* **Progress Tracking**: Completed
  - Progress tracker service (src/services/progress_tracker.py)
  - Progress API endpoints (src/api/progress.py)
  - Real-time progress calculation based on current data

### In Progress Components 🚧

* **Badges System**: Partially Implemented
  - Database table exists with schema
  - Basic badge methods in database.py
  - **MISSING**: Badge service layer, badge API, badge definitions JSON, UI integration

### MVP SIMPLIFICATION - August 2025

**Decision**: Project scope reduced to essential MVP functionality based on user feedback: "I want it to look good and show me my data and progress (like charts) and that's really it. The shortest path to polished completion."

### MVP Features Implemented ✅

* **Core Data Display**: Today & Week views with essential health metrics
* **Data Visualization**: Charts for weight, heart rate, steps, HRV trends
* **Mixed Data Flow**: 
  - Automated: Steps & sleeping HR (Tasker → Health Connect → Pi)
  - Manual triggers: Weight entry (Samsung Health → Tasker → Pi)
  - Manual touchscreen: HRV entry directly on Pi
* **Historical Data Import**: Direct database insertion script for existing data
* **Complete Configuration**: Detailed Tasker setup with exact JSON payloads
* **Touch-Optimized UI**: Designed for Raspberry Pi 7" touchscreen
* **Real-Time Sync**: Background job scheduler for data processing

### Features Deferred (Beyond MVP) ❌

* **ADHD-Friendly Features**: Focus Mode, confetti animations, minimal iconography
* **Motivational Nudges**: Morning/evening cards, quiet hours
* **Settings Management**: Advanced UI customization, data export/import
* **Benchmarks**: Week/month comparison analytics
* **Goals & Streaks**: Achievement tracking and gamification
* **Badges System**: Milestone rewards and progress recognition

### MVP Completion Status

* **Codebase**: ✅ Cleaned and simplified, production-ready
* **Data Integration**: ✅ 4 days historical data imported
* **Server**: ✅ Running on Pi at http://192.168.86.36:8000
* **Dashboard**: ✅ Available with Today/Week views
* **Tasker Config**: ✅ Complete setup guide with JSON payloads
* **Documentation**: ✅ README, setup guides, configuration docs

**Result**: Functional health dashboard ready for daily use with automated data sync and manual entry capabilities.

