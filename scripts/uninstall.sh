#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="motionberry"

echo "Uninstalling Motionberry..."

# Stop the Supervisor service
if supervisorctl status "$SERVICE_NAME" | grep -q 'RUNNING'; then
    echo "Stopping Motionberry service..."
    sudo supervisorctl stop "$SERVICE_NAME"
fi

# Remove Supervisor configuration file
SUPERVISOR_CONF_FILE="/etc/supervisor/conf.d/$SERVICE_NAME.conf"
if [ -f "$SUPERVISOR_CONF_FILE" ]; then
    echo "Removing Supervisor configuration file..."
    sudo rm -f "$SUPERVISOR_CONF_FILE"
    sudo supervisorctl reread
    sudo supervisorctl update
fi

# # Remove Python virtual environment
# if [ -d "$PYTHON_ENV_DIR" ]; then
#     echo "Removing virtual environment..."
#     rm -rf "$PYTHON_ENV_DIR"
# fi

echo "Do you want to remove system dependencies installed by Motionberry? (y/n)"
read -r REMOVE_DEPS
if [[ "$REMOVE_DEPS" =~ ^[Yy]$ ]]; then
    echo "Removing system dependencies..."
    sudo apt purge -y --auto-remove ffmpeg python3-dev python3-venv python3-pip python3-numpy python3-picamera2
fi

echo "Motionberry uninstallation complete."
