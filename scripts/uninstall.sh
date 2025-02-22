#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="motionberry.service"
LOGROTATE_FILE="/etc/logrotate.d/motionberry"
LOG_FILE="/var/log/motionberry.log"

echo "Uninstalling Motionberry..."

# Stop and disable the Motionberry service
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Stopping Motionberry service..."
    sudo systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME"; then
    echo "Disabling Motionberry service..."
    sudo systemctl disable "$SERVICE_NAME"
fi

# Remove the systemd service file
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
if [ -f "$SERVICE_FILE" ]; then
    echo "Removing systemd service file..."
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

# Remove the logrotate configuration
if [ -f "$LOGROTATE_FILE" ]; then
    echo "Removing logrotate configuration..."
    sudo rm -f "$LOGROTATE_FILE"
fi

# Remove the virtual environment
if [ -d "$PYTHON_ENV_DIR" ]; then
    echo "Removing virtual environment..."
    rm -rf "$PYTHON_ENV_DIR"
fi

# Detect OS version
OS_VERSION=$(lsb_release -cs)

# Remove system dependencies
echo "Do you want to remove system dependencies installed by Motionberry? (y/n)"
read -r REMOVE_DEPS
if [[ "$REMOVE_DEPS" =~ ^[Yy]$ ]]; then
    echo "Removing system dependencies..."
    sudo apt purge -y --auto-remove \
        util-linux \
        mkvtoolnix \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-numpy \
        python3-picamera2

    # Remove GPAC (built from source or installed via apt)
    if [ "$OS_VERSION" = "bookworm" ]; then
        echo "Uninstalling GPAC (built from source)..."
        sudo rm -f /usr/local/bin/MP4Box
        sudo rm -rf /usr/local/include/gpac
        sudo rm -rf /usr/local/lib/libgpac*
        sudo rm -rf /usr/local/share/gpac
    else
        echo "Uninstalling GPAC (installed via apt)..."
        sudo apt purge -y --auto-remove gpac
    fi

    # Remove GPAC build dependencies (if applicable)
    if [ "$OS_VERSION" = "bookworm" ]; then
        sudo apt purge -y --auto-remove \
            build-essential \
            cmake \
            git \
            zlib1g-dev \
            libfreetype6-dev \
            libjpeg62-turbo-dev \
            libpng-dev \
            libmad0-dev \
            libfaad-dev \
            libogg-dev \
            libvorbis-dev \
            libtheora-dev \
            liba52-0.7.4-dev \
            libavcodec-dev \
            libavformat-dev \
            libavutil-dev \
            libswscale-dev \
            libavdevice-dev \
            libnghttp2-dev \
            libopenjp2-7-dev \
            libcaca-dev \
            libxv-dev \
            x11proto-video-dev \
            libgl1-mesa-dev \
            libglu1-mesa-dev \
            x11proto-gl-dev \
            libxvidcore-dev \
            libssl-dev \
            libjack-jackd2-dev \
            libasound2-dev \
            libpulse-dev \
            libsdl2-dev \
            dvb-apps \
            mesa-utils
    fi
fi

echo "Motionberry uninstallation complete."
