# HealthTracker Kiosk Setup Guide

Complete guide for setting up HealthTracker as a production kiosk on Raspberry Pi with touchscreen.

## 📋 Prerequisites

- Raspberry Pi 5 (or Pi 4) with Raspbian OS installed
- 7-inch touchscreen connected and working
- Network connection configured
- HealthTracker repository cloned to `/home/davidpm/healthtracker`

## 🚀 Quick Setup

Run the automated setup script:

```bash
cd /home/davidpm/healthtracker/scripts/kiosk
sudo bash setup-kiosk.sh
```

This will:
- Install all required packages
- Configure systemd services
- Set up touch optimization
- Enable auto-login and kiosk mode
- Configure power management

## 📦 Manual Setup Steps

### 1. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    chromium-browser \
    unclutter \
    python3-pip \
    sqlite3 \
    xinput \
    xdotool

cd /home/davidpm/healthtracker
pip3 install -r requirements.txt
```

### 2. Install Systemd Services

```bash
# Copy service files
sudo cp scripts/kiosk/healthtracker-server.service /etc/systemd/system/
sudo cp scripts/kiosk/healthtracker-kiosk.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable healthtracker-server
sudo systemctl enable healthtracker-kiosk

# Start services now
sudo systemctl start healthtracker-server
sudo systemctl start healthtracker-kiosk
```

### 3. Configure Display & Touch

#### Screen Rotation (if needed)
Edit `/boot/config.txt`:
```bash
# Add one of these lines depending on orientation:
display_rotate=0  # Normal
display_rotate=1  # 90 degrees
display_rotate=2  # 180 degrees
display_rotate=3  # 270 degrees
```

#### Touch Calibration
```bash
# Install calibration tool
sudo apt-get install xinput-calibrator

# Run calibration
xinput_calibrator

# Save output to /etc/X11/xorg.conf.d/99-calibration.conf
```

### 4. Disable Screen Blanking

Edit `/etc/lightdm/lightdm.conf`:
```ini
[Seat:*]
xserver-command=X -s 0 -dpms
```

Create `/home/davidpm/.config/lxsession/LXDE-pi/autostart`:
```bash
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xset s off
@xset -dpms
@xset s noblank
```

### 5. Hide Mouse Cursor

Enable unclutter service:
```bash
sudo systemctl enable unclutter
sudo systemctl start unclutter
```

### 6. Configure Auto-Login

Edit `/etc/lightdm/lightdm.conf`:
```ini
[Seat:*]
autologin-user=davidpm
autologin-user-timeout=0
```

## 🔧 Configuration

### Environment Variables

Create `/home/davidpm/healthtracker/.env`:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security (for local network only)
ALLOWED_IPS=192.168.1.0/24
SECRET_KEY=your-secret-key-here

# Database
DATABASE_PATH=/home/davidpm/healthtracker/healthtracker.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/healthtracker
```

### Chromium Kiosk Flags

The service uses these optimized flags:
- `--kiosk` - Full screen mode
- `--incognito` - No saved data
- `--noerrdialogs` - No error dialogs
- `--disable-infobars` - No info bars
- `--disable-pinch` - No pinch zoom
- `--overscroll-history-navigation=0` - No swipe navigation
- `--touch-events=enabled` - Enable touch
- `--enable-touch-drag-drop` - Touch drag support

## 🖥️ Display Optimizations

### CSS Touch Optimizations

The kiosk includes `kiosk-touch.css` with:
- 44px minimum touch targets
- Disabled text selection
- Smooth momentum scrolling
- Touch feedback animations
- Optimized for 1024x600 and 800x480 displays

### Performance Settings

- Hardware acceleration enabled
- GPU sandboxing disabled for Pi
- Shared memory usage optimized
- Cache and temp files in RAM

## 🔍 Health Monitoring

### Automatic Health Checks

Set up cron job for health monitoring:
```bash
# Edit crontab
crontab -e

# Add health check every 15 minutes
*/15 * * * * /home/davidpm/healthtracker/scripts/kiosk/monitor-health.sh
```

### Manual Health Check

```bash
# Run health check
bash /home/davidpm/healthtracker/scripts/kiosk/monitor-health.sh

# Check service status
sudo systemctl status healthtracker-server
sudo systemctl status healthtracker-kiosk

# View logs
sudo journalctl -u healthtracker-server -f
sudo journalctl -u healthtracker-kiosk -f
```

## 🛠️ Maintenance

### Enter Maintenance Mode

```bash
# Stop kiosk (keeps server running)
bash /home/davidpm/healthtracker/scripts/kiosk/maintenance-mode.sh

# Restart kiosk
sudo systemctl start healthtracker-kiosk
```

### Recovery Mode

If system has issues:
```bash
# Run recovery script
bash /home/davidpm/healthtracker/scripts/kiosk/recovery.sh
```

This will:
- Stop all services
- Clear caches
- Check database integrity
- Restart services

### Update Application

```bash
# Enter maintenance mode
bash scripts/kiosk/maintenance-mode.sh

# Pull updates
cd /home/davidpm/healthtracker
git pull

# Install new dependencies
pip3 install -r requirements.txt

# Restart services
sudo systemctl restart healthtracker-server
sudo systemctl restart healthtracker-kiosk
```

## 📊 Logging

Logs are stored in `/var/log/healthtracker/`:
- `server.log` - FastAPI application logs
- `server-error.log` - Server errors only
- `kiosk.log` - Chromium kiosk logs
- `kiosk-error.log` - Kiosk errors only
- `health-check.log` - System health checks
- `recovery.log` - Recovery actions
- `performance.log` - Performance metrics

### Log Rotation

Logs rotate automatically:
- General logs: 10MB max, 5 backups
- Error logs: 5MB max, 3 backups
- Old logs cleaned after 7 days

### View Logs

```bash
# Real-time server logs
tail -f /var/log/healthtracker/server.log

# Today's errors
grep "$(date +%Y-%m-%d)" /var/log/healthtracker/server-error.log

# Performance metrics
tail -f /var/log/healthtracker/performance.log
```

## 🔒 Security

### Network Security

- API binds to localhost only by default
- IP filtering for external access
- No authentication for local-only setup

### File Permissions

```bash
# Set proper ownership
sudo chown -R davidpm:davidpm /home/davidpm/healthtracker

# Secure database
chmod 600 /home/davidpm/healthtracker/healthtracker.db

# Protect logs
sudo chown -R davidpm:davidpm /var/log/healthtracker
chmod 750 /var/log/healthtracker
```

## 🧪 Testing

### Test Touch Interface

```bash
# Test touch events
evtest

# Test touch coordinates
xinput test-xi2
```

### Test API

```bash
# Health check
curl http://localhost:8000/health

# Database check
curl http://localhost:8000/api/health/db

# UI check
curl http://localhost:8000/static/index.html
```

### Performance Testing

```bash
# Monitor resource usage
htop

# Check memory
free -h

# Check disk
df -h

# Database size
du -h /home/davidpm/healthtracker/healthtracker.db
```

## 🔄 Backup & Recovery

### Automated Backups

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * sqlite3 /home/davidpm/healthtracker/healthtracker.db ".backup /home/davidpm/backups/healthtracker-$(date +\%Y\%m\%d).db"

# Keep only last 7 backups
0 3 * * * find /home/davidpm/backups -name "healthtracker-*.db" -mtime +7 -delete
```

### Manual Backup

```bash
# Backup database
sqlite3 healthtracker.db ".backup healthtracker-backup.db"

# Backup entire application
tar -czf healthtracker-backup.tar.gz /home/davidpm/healthtracker
```

### Restore from Backup

```bash
# Stop services
sudo systemctl stop healthtracker-server

# Restore database
cp /path/to/backup.db /home/davidpm/healthtracker/healthtracker.db

# Restart services
sudo systemctl start healthtracker-server
```

## 🚨 Troubleshooting

### Kiosk Won't Start

```bash
# Check X display
echo $DISPLAY  # Should be :0

# Test X server
DISPLAY=:0 xset q

# Check permissions
ls -la ~/.Xauthority
```

### Touch Not Working

```bash
# List input devices
xinput list

# Test touch device
xinput test [device-id]

# Recalibrate
xinput_calibrator
```

### API Not Responding

```bash
# Check if port is in use
sudo netstat -tlnp | grep 8000

# Check Python path
which python3

# Test direct start
cd /home/davidpm/healthtracker
python3 start_server.py
```

### High CPU/Memory Usage

```bash
# Restart services
sudo systemctl restart healthtracker-server
sudo systemctl restart healthtracker-kiosk

# Clear caches
rm -rf ~/.cache/chromium
rm -rf ~/.config/chromium-kiosk/Default/Cache

# Run recovery
bash scripts/kiosk/recovery.sh
```

## 📈 Performance Tuning

### Raspberry Pi Optimization

Edit `/boot/config.txt`:
```ini
# Overclock (Pi 4/5 only, use with cooling)
over_voltage=6
arm_freq=2000
gpu_freq=750

# GPU memory split
gpu_mem=128

# Disable unnecessary features
dtoverlay=disable-bt
dtoverlay=disable-wifi  # Only if using Ethernet
```

### Swap Configuration

```bash
# Increase swap size
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Database Optimization

```bash
# Optimize database periodically
sqlite3 healthtracker.db "VACUUM;"
sqlite3 healthtracker.db "ANALYZE;"
sqlite3 healthtracker.db "PRAGMA optimize;"
```

## ✅ Production Checklist

Before going live:

- [ ] Services enabled for auto-start
- [ ] Auto-login configured
- [ ] Screen blanking disabled
- [ ] Mouse cursor hidden
- [ ] Touch calibrated
- [ ] Network configured (static IP recommended)
- [ ] Backups scheduled
- [ ] Health monitoring enabled
- [ ] Logs rotating properly
- [ ] Recovery tested
- [ ] Power failure tested
- [ ] Documentation updated

## 📞 Support

For issues:
1. Check logs in `/var/log/healthtracker/`
2. Run health check: `bash scripts/kiosk/monitor-health.sh`
3. Try recovery: `bash scripts/kiosk/recovery.sh`
4. Review this documentation
5. Check systemd status: `systemctl status healthtracker-*`

---

Last updated: 2025