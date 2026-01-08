#!/bin/bash
# Install and start the health import watcher service

set -e

PLIST_FILE="$HOME/Library/LaunchAgents/com.daleb.health-import-watcher.plist"
PROJECT_DIR="/Users/daleb/Documents/projects/health-tracking-app"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=" | tr '=' '=' | head -c 70 && echo
echo "Health Import Watcher Installation"
echo "=" | tr '=' '=' | head -c 70 && echo
echo

# Create logs directory
echo "Creating logs directory..."
mkdir -p "$PROJECT_DIR/logs"

# Install watchdog dependency
echo "Installing dependencies..."
cd "$PROJECT_DIR"
uv pip install watchdog>=5.0.0

# Copy plist file
echo "Installing LaunchAgent..."
cp "$SCRIPT_DIR/com.daleb.health-import-watcher.plist" "$PLIST_FILE"

# Unload if already loaded (ignore errors)
launchctl unload "$PLIST_FILE" 2>/dev/null || true

# Load the service
echo "Loading service..."
launchctl load "$PLIST_FILE"

# Wait a moment for it to start
sleep 2

# Check status
echo
echo "Checking status..."
if launchctl list | grep -q health-import-watcher; then
    echo "✅ Service is running"
else
    echo "⚠️  Service may not be running - check logs"
fi

echo
echo "=" | tr '=' '=' | head -c 70 && echo
echo "Installation complete!"
echo "=" | tr '=' '=' | head -c 70 && echo
echo
echo "The watcher is now monitoring: /Users/daleb/Documents/health/"
echo "Drop export.zip files there to trigger automatic import."
echo
echo "Useful commands:"
echo "  Stop:   launchctl unload $PLIST_FILE"
echo "  Start:  launchctl load $PLIST_FILE"
echo "  Status: launchctl list | grep health-import-watcher"
echo "  Logs:   tail -f $PROJECT_DIR/logs/import_history.log"
echo
