#!/bin/bash
# Uninstall the health import watcher service

PLIST_FILE="$HOME/Library/LaunchAgents/com.daleb.health-import-watcher.plist"

echo "=" | tr '=' '=' | head -c 70 && echo
echo "Health Import Watcher Uninstallation"
echo "=" | tr '=' '=' | head -c 70 && echo
echo

echo "Stopping service..."
launchctl unload "$PLIST_FILE" 2>/dev/null || echo "Service was not running"

echo "Removing plist file..."
rm -f "$PLIST_FILE"

echo
echo "=" | tr '=' '=' | head -c 70 && echo
echo "Uninstallation complete!"
echo "=" | tr '=' '=' | head -c 70 && echo
echo
echo "The watcher service has been removed."
echo "Log files in logs/ directory were preserved."
echo
