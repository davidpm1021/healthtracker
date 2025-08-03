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

## Current Status

* **Current Phase:** Phase 1 - Foundation
* **Current Sub-Component:** Hardware and OS setup
* **Current Chunk:** Chunk 5 - Network and Security Configuration
* **Approval Status:** Phase 1 breakdown approved

## Approval Gates

* [x] Phase 1 breakdown approved
* [ ] Phase 2 breakdown approved
* [ ] Phase 3 breakdown approved
* [ ] Phase 4 breakdown approved

## Implementation Log

* **Chunk 1 - Raspberry Pi OS Installation and Initial Configuration**: Completed
  - Raspberry Pi OS installed and configured
  - SSH enabled and network connectivity established
  - Hostname set to "healthtracker"

* **Chunk 2 - Display Driver and Touch Screen Setup**: Completed
  - Display orientation configured correctly
  - Touch input registered and working
  - Display resolution optimized for 7-inch screen

* **Chunk 3 - Touch Calibration and Input Configuration**: Completed
  - Touch input precisely calibrated
  - Single-touch mode configured
  - Calibration matrix saved for recovery

* **Chunk 4 - System Performance and Boot Optimization**: Completed
  - Boot time optimized to under 30 seconds
  - Unnecessary services disabled
  - Power management configured for always-on display
  - Swap configured appropriately

