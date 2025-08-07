#!/bin/bash
# Remote Installation Script for HealthTracker Kiosk
# This script deploys and configures everything in one command

set -e

# Configuration
PI_HOST="davidpm@192.168.86.36"
PI_PROJECT_DIR="/home/davidpm/healthtracker"
LOCAL_PROJECT_DIR="/mnt/c/Users/Dave/Cursor/HealthTracker"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 HealthTracker Kiosk Remote Deployment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Check connectivity
echo -e "${YELLOW}Step 1: Checking Pi connectivity...${NC}"
if ! ping -c 1 192.168.86.36 > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot reach Pi at 192.168.86.36${NC}"
    echo "Troubleshooting steps:"
    echo "  1. Check if Pi is powered on"
    echo "  2. Verify network connection"
    echo "  3. Confirm IP address: ping raspberrypi.local"
    exit 1
fi
echo -e "${GREEN}✅ Pi is reachable${NC}"

# Step 2: Create deployment package
echo -e "${YELLOW}Step 2: Creating deployment package...${NC}"
cd "$LOCAL_PROJECT_DIR"
TEMP_DEPLOY="/tmp/healthtracker_kiosk_deploy.tar.gz"

tar -czf "$TEMP_DEPLOY" \
    scripts/kiosk/ \
    src/logging_config.py \
    src/main.py \
    static/css/kiosk-touch.css \
    static/index.html \
    KIOSK_SETUP.md

echo -e "${GREEN}✅ Deployment package created${NC}"

# Step 3: Upload package
echo -e "${YELLOW}Step 3: Uploading to Pi...${NC}"
scp "$TEMP_DEPLOY" $PI_HOST:/tmp/
echo -e "${GREEN}✅ Package uploaded${NC}"

# Step 4: Extract and configure on Pi
echo -e "${YELLOW}Step 4: Configuring on Pi...${NC}"

ssh $PI_HOST << 'REMOTE_SCRIPT'
set -e

# Extract package
cd /home/davidpm/healthtracker
tar -xzf /tmp/healthtracker_kiosk_deploy.tar.gz

# Make scripts executable
chmod +x scripts/kiosk/*.sh

# Create log directory
sudo mkdir -p /var/log/healthtracker
sudo chown davidpm:davidpm /var/log/healthtracker

# Install Python dependencies if needed
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
fi

# Stop existing services if running
sudo systemctl stop healthtracker-server 2>/dev/null || true
sudo systemctl stop healthtracker-kiosk 2>/dev/null || true

echo "Files extracted and configured"
REMOTE_SCRIPT

echo -e "${GREEN}✅ Remote configuration complete${NC}"

# Step 5: Run setup script
echo -e "${YELLOW}Step 5: Running kiosk setup...${NC}"
echo "This will configure systemd services and system settings"
echo "You may be prompted for sudo password..."

ssh -t $PI_HOST "cd $PI_PROJECT_DIR && sudo bash scripts/kiosk/setup-kiosk.sh"

# Step 6: Start services
echo -e "${YELLOW}Step 6: Starting services...${NC}"

ssh $PI_HOST << 'START_SERVICES'
# Enable services
sudo systemctl enable healthtracker-server
sudo systemctl enable healthtracker-kiosk
sudo systemctl enable healthtracker-monitor.timer

# Start services
sudo systemctl start healthtracker-server
sleep 3

# Check if server is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Server is running"
    sudo systemctl start healthtracker-kiosk
    echo "✅ Kiosk started"
else
    echo "❌ Server failed to start"
    sudo journalctl -u healthtracker-server -n 20
fi
START_SERVICES

# Step 7: Verify installation
echo -e "${YELLOW}Step 7: Verifying installation...${NC}"

ssh $PI_HOST << 'VERIFY'
echo "Service Status:"
echo "───────────────"
systemctl is-active healthtracker-server || echo "Server: inactive"
systemctl is-active healthtracker-kiosk || echo "Kiosk: inactive"

echo ""
echo "API Health Check:"
echo "─────────────────"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not responding"

echo ""
echo "Recent Logs:"
echo "────────────"
sudo journalctl -u healthtracker-server -n 5 --no-pager
VERIFY

# Cleanup
rm -f "$TEMP_DEPLOY"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Deployment Complete!${NC}"
echo ""
echo "Dashboard URL: http://192.168.86.36:8000/static/index.html"
echo ""
echo "Useful commands:"
echo "  Check status:  ssh $PI_HOST 'sudo systemctl status healthtracker-*'"
echo "  View logs:     ssh $PI_HOST 'sudo journalctl -u healthtracker-server -f'"
echo "  Maintenance:   ssh $PI_HOST 'bash ~/healthtracker/scripts/kiosk/maintenance-mode.sh'"
echo "  Recovery:      ssh $PI_HOST 'bash ~/healthtracker/scripts/kiosk/recovery.sh'"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"