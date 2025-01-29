#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR=".venv"
SERVICE_NAME="motionberry"

echo "Installing required libraries..."
sudo apt update
sudo apt install -y --no-install-recommends \
    util-linux \
    ffmpeg \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-numpy \
    python3-picamera2 \
    supervisor

echo "Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv --system-site-packages "$PYTHON_ENV_DIR"
. "$PYTHON_ENV_DIR/bin/activate"
pip install --upgrade pip
pip install .

# Supervisor configuration
SUPERVISOR_CONF_DIR="/etc/supervisor/conf.d"
SUPERVISOR_CONF_FILE="$SUPERVISOR_CONF_DIR/$SERVICE_NAME.conf"

if [ ! -f "$SUPERVISOR_CONF_FILE" ]; then
    echo "Creating Supervisor configuration file..."
    sudo tee "$SUPERVISOR_CONF_FILE" > /dev/null <<EOF
[program:$SERVICE_NAME]
command=$APP_DIR/$PYTHON_ENV_DIR/bin/python $APP_DIR/run.py
directory=$APP_DIR
autostart=true
autorestart=true
stderr_logfile=/var/log/$SERVICE_NAME.err.log
stdout_logfile=/var/log/$SERVICE_NAME.out.log
user=$(whoami)
environment=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$APP_DIR/$PYTHON_ENV_DIR/bin"
EOF
else
    echo "Supervisor configuration file already exists."
fi

echo "Reloading Supervisor, enabling, and starting the Motionberry service..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start "$SERVICE_NAME"

echo "Motionberry setup complete. Service status:"
sudo supervisorctl status "$SERVICE_NAME"
