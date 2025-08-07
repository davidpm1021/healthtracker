#!/bin/bash
# Deploy updates to Pi and restart server with correct ingestion endpoint
# Usage: bash deploy_and_restart.sh

set -e

# Configuration
PI_HOST="davidpm@192.168.86.36"
PI_PROJECT_DIR="/home/davidpm/healthtracker"
LOCAL_PROJECT_DIR="$(dirname "$0")"

echo "🚀 Deploying HealthTracker updates to Pi..."
echo "======================================="

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

# Deploy main server file that includes ingestion
echo "Deploying server files..."
scp "$LOCAL_PROJECT_DIR/src/main.py" $PI_HOST:$PI_PROJECT_DIR/src/
scp "$LOCAL_PROJECT_DIR/src/api/ingest.py" $PI_HOST:$PI_PROJECT_DIR/src/api/
scp "$LOCAL_PROJECT_DIR/start_server.py" $PI_HOST:$PI_PROJECT_DIR/

# Deploy validator updates for flexible data formats
echo "Deploying validator updates..."
scp "$LOCAL_PROJECT_DIR/src/validators.py" $PI_HOST:$PI_PROJECT_DIR/src/

# Deploy database module
echo "Deploying database module..."
scp "$LOCAL_PROJECT_DIR/src/database.py" $PI_HOST:$PI_PROJECT_DIR/src/

# Deploy test script
echo "Deploying test script..."
scp "$LOCAL_PROJECT_DIR/test_ingestion.sh" $PI_HOST:$PI_PROJECT_DIR/
ssh $PI_HOST "chmod +x $PI_PROJECT_DIR/test_ingestion.sh"

# Stop any running servers
echo "Stopping existing servers..."
ssh $PI_HOST "pkill -f 'python3' || true"
sleep 2

# Start the server (only one version now)
echo "Starting Health Tracker server..."
ssh $PI_HOST "cd $PI_PROJECT_DIR && nohup python3 start_server.py > server.log 2>&1 &"
sleep 3

# Verify server is running
echo "Verifying server status..."
if ssh $PI_HOST "curl -s http://localhost:8000/health > /dev/null 2>&1"; then
    echo "✅ Server is running!"
else
    echo "⚠️  Server may not have started correctly"
    echo "Check logs with: ssh $PI_HOST 'tail -f $PI_PROJECT_DIR/server.log'"
fi

# Test ingestion endpoint
echo ""
echo "Testing ingestion endpoint..."
TEST_RESPONSE=$(ssh $PI_HOST "curl -s -X POST http://localhost:8000/api/ingest/test")
if echo "$TEST_RESPONSE" | grep -q "healthy"; then
    echo "✅ Ingestion endpoint is working!"
else
    echo "⚠️  Ingestion endpoint test failed"
    echo "Response: $TEST_RESPONSE"
fi

echo ""
echo "======================================="
echo "✅ Deployment complete!"
echo ""
echo "Dashboard: http://192.168.86.36:8000/static/index.html"
echo "API Docs: http://192.168.86.36:8000/docs"
echo ""
echo "Run test ingestion:"
echo "  ssh $PI_HOST '$PI_PROJECT_DIR/test_ingestion.sh'"
echo ""
echo "Or from your local machine:"
echo "  bash test_ingestion.sh"