#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="motionberry.service"

echo "Uninstalling Motionberry..."

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Stopping Motionberry service..."
    sudo systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME"; then
    echo "Disabling Motionberry service..."
    sudo systemctl disable "$SERVICE_NAME"
fi

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
if [ -f "$SERVICE_FILE" ]; then
    echo "Removing systemd service file..."
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

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
