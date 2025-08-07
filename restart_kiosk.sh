#!/bin/bash
echo "🔄 Restarting Health Tracker Kiosk..."

# Kill any existing processes
pkill -f mvp_server.py
pkill -f chromium
sleep 2

# Start the MVP server
echo "🚀 Starting MVP server..."
python3 mvp_server.py &
SERVER_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server..."
sleep 3

# Test server is responsive
if curl -s http://localhost:8000/api/ui/today > /dev/null; then
    echo "✅ Server is responding"
else
    echo "❌ Server not responding"
    exit 1
fi

# Start Chromium in kiosk mode
echo "🖥️ Starting kiosk..."
DISPLAY=:0 chromium-browser \
    --kiosk \
    --no-first-run \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --user-data-dir=/tmp/chromium-kiosk-$$ \
    http://localhost:8000/static/index.html &

echo "✨ Kiosk started! Touch navigation should now work."
echo "📱 Try swiping left/right to navigate between Today and Charts"