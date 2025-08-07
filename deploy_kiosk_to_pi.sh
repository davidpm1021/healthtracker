#!/bin/bash
# Deploy Kiosk Configuration to Raspberry Pi
# Run this script when Pi is accessible: bash deploy_kiosk_to_pi.sh

set -e

# Configuration
PI_HOST="davidpm@192.168.86.36"
PI_PROJECT_DIR="/home/davidpm/healthtracker"

echo "🚀 Deploying HealthTracker Kiosk Configuration to Pi..."

# Check if Pi is reachable
echo "Checking Pi connectivity..."
if ! ping -c 1 192.168.86.36 > /dev/null 2>&1; then
    echo "❌ Cannot reach Pi at 192.168.86.36"
    echo "Please ensure:"
    echo "  1. Pi is powered on"
    echo "  2. Connected to network"
    echo "  3. IP address is correct"
    exit 1
fi

echo "✅ Pi is reachable"

# Create remote directories if needed
echo "Creating remote directories..."
ssh $PI_HOST "mkdir -p $PI_PROJECT_DIR/scripts/kiosk $PI_PROJECT_DIR/src $PI_PROJECT_DIR/static/css"

# Copy kiosk scripts
echo "Copying kiosk scripts..."
scp scripts/kiosk/*.sh $PI_HOST:$PI_PROJECT_DIR/scripts/kiosk/
scp scripts/kiosk/*.service $PI_HOST:$PI_PROJECT_DIR/scripts/kiosk/
scp scripts/kiosk/*.timer $PI_HOST:$PI_PROJECT_DIR/scripts/kiosk/

# Copy Python logging configuration
echo "Copying logging configuration..."
scp src/logging_config.py $PI_HOST:$PI_PROJECT_DIR/src/

# Copy CSS improvements
echo "Copying CSS files..."
scp static/css/kiosk-touch.css $PI_HOST:$PI_PROJECT_DIR/static/css/

# Copy updated main.py
echo "Copying updated main.py..."
scp src/main.py $PI_HOST:$PI_PROJECT_DIR/src/

# Copy documentation
echo "Copying documentation..."
scp KIOSK_SETUP.md $PI_HOST:$PI_PROJECT_DIR/

# Make scripts executable
echo "Setting permissions..."
ssh $PI_HOST "chmod +x $PI_PROJECT_DIR/scripts/kiosk/*.sh"

# Run the setup script on Pi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Files deployed successfully!"
echo ""
echo "Now SSH into the Pi and run the setup:"
echo "  ssh $PI_HOST"
echo "  cd $PI_PROJECT_DIR"
echo "  sudo bash scripts/kiosk/setup-kiosk.sh"
echo ""
echo "Or run remotely:"
echo "  ssh $PI_HOST 'cd $PI_PROJECT_DIR && sudo bash scripts/kiosk/setup-kiosk.sh'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"