#!/bin/bash
# HealthTracker Kiosk Setup Script
# Run with: sudo bash setup-kiosk.sh

set -e

echo "🚀 Setting up HealthTracker Kiosk..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}1. Installing required packages...${NC}"
apt-get update
apt-get install -y \
    chromium-browser \
    unclutter \
    xdotool \
    xinput \
    curl \
    python3-pip \
    sqlite3

echo -e "${GREEN}2. Creating log directory...${NC}"
mkdir -p /var/log/healthtracker
chown pi:pi /var/log/healthtracker

echo -e "${GREEN}3. Setting up unclutter to hide mouse cursor...${NC}"
cat > /etc/systemd/system/unclutter.service << 'EOF'
[Unit]
Description=Hide mouse cursor when inactive
After=graphical.target

[Service]
Type=simple
User=pi
Environment="DISPLAY=:0"
ExecStart=/usr/bin/unclutter -idle 0.1 -root
Restart=always

[Install]
WantedBy=graphical.target
EOF

echo -e "${GREEN}4. Configuring screen blanking prevention...${NC}"
# Disable screen blanking in lightdm
if [ -f /etc/lightdm/lightdm.conf ]; then
    if ! grep -q "xserver-command" /etc/lightdm/lightdm.conf; then
        sed -i '/\[Seat:\*\]/a xserver-command=X -s 0 -dpms' /etc/lightdm/lightdm.conf
    fi
fi

# Add screen blanking prevention to autostart
mkdir -p /home/pi/.config/lxsession/LXDE-pi/
cat > /home/pi/.config/lxsession/LXDE-pi/autostart << 'EOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xset s off
@xset -dpms
@xset s noblank
EOF
chown -R pi:pi /home/pi/.config

echo -e "${GREEN}5. Setting up power management...${NC}"
# Disable WiFi power management
if [ -f /etc/rc.local ]; then
    if ! grep -q "iwconfig wlan0 power off" /etc/rc.local; then
        sed -i '/^exit 0/i iwconfig wlan0 power off' /etc/rc.local
    fi
fi

echo -e "${GREEN}6. Installing systemd services...${NC}"
cp healthtracker-server.service /etc/systemd/system/
cp healthtracker-kiosk.service /etc/systemd/system/
systemctl daemon-reload

echo -e "${GREEN}7. Setting up auto-login for pi user...${NC}"
# Enable auto-login in raspi-config style
systemctl set-default graphical.target
sed -i 's/^#*autologin-user=.*/autologin-user=pi/' /etc/lightdm/lightdm.conf
sed -i 's/^#*autologin-user-timeout=.*/autologin-user-timeout=0/' /etc/lightdm/lightdm.conf

echo -e "${GREEN}8. Creating recovery script...${NC}"
cat > /home/pi/healthtracker/scripts/kiosk/recovery.sh << 'EOF'
#!/bin/bash
# Emergency recovery script

echo "🔧 Running HealthTracker recovery..."

# Stop services
sudo systemctl stop healthtracker-kiosk
sudo systemctl stop healthtracker-server

# Clear chromium cache
rm -rf /home/pi/.config/chromium-kiosk/*

# Check database integrity
sqlite3 /home/pi/healthtracker/healthtracker.db "PRAGMA integrity_check;"

# Restart services
sudo systemctl start healthtracker-server
sleep 5
sudo systemctl start healthtracker-kiosk

echo "✅ Recovery complete"
EOF
chmod +x /home/pi/healthtracker/scripts/kiosk/recovery.sh
chown pi:pi /home/pi/healthtracker/scripts/kiosk/recovery.sh

echo -e "${GREEN}9. Creating maintenance mode script...${NC}"
cat > /home/pi/healthtracker/scripts/kiosk/maintenance-mode.sh << 'EOF'
#!/bin/bash
# Enter maintenance mode (exit kiosk)

echo "🔧 Entering maintenance mode..."
sudo systemctl stop healthtracker-kiosk
echo "Kiosk stopped. Use 'sudo systemctl start healthtracker-kiosk' to restart"
EOF
chmod +x /home/pi/healthtracker/scripts/kiosk/maintenance-mode.sh
chown pi:pi /home/pi/healthtracker/scripts/kiosk/maintenance-mode.sh

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Kiosk setup complete!${NC}"
echo ""
echo "To enable services on boot:"
echo -e "${YELLOW}  sudo systemctl enable healthtracker-server${NC}"
echo -e "${YELLOW}  sudo systemctl enable healthtracker-kiosk${NC}"
echo -e "${YELLOW}  sudo systemctl enable unclutter${NC}"
echo ""
echo "To start services now:"
echo -e "${YELLOW}  sudo systemctl start healthtracker-server${NC}"
echo -e "${YELLOW}  sudo systemctl start healthtracker-kiosk${NC}"
echo -e "${YELLOW}  sudo systemctl start unclutter${NC}"
echo ""
echo "Maintenance commands:"
echo -e "${YELLOW}  ~/healthtracker/scripts/kiosk/maintenance-mode.sh${NC} - Exit kiosk"
echo -e "${YELLOW}  ~/healthtracker/scripts/kiosk/recovery.sh${NC} - Recovery mode"
echo -e "${YELLOW}  sudo journalctl -u healthtracker-server -f${NC} - View server logs"
echo -e "${YELLOW}  sudo journalctl -u healthtracker-kiosk -f${NC} - View kiosk logs"
echo ""
echo -e "${GREEN}Reboot recommended to ensure all settings take effect.${NC}"