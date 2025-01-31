#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR=".venv"
SERVICE_NAME="motionberry.service"
LOG_FILE="/var/log/motionberry.log"
USER_NAME=$(whoami)  # Get the current user

echo "Installing required libraries..."
sudo apt update
sudo apt install -y --no-install-recommends \
    util-linux \
    mkvtoolnix \
    gpac \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-numpy \
    python3-picamera2

echo "Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv --system-site-packages "$PYTHON_ENV_DIR"
. "$PYTHON_ENV_DIR/bin/activate"
pip install --upgrade pip
pip install .

echo "Setting up log rotation for $LOG_FILE..."
sudo tee /etc/logrotate.d/motionberry > /dev/null <<EOF
$LOG_FILE {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 644 $USER_NAME $USER_NAME
}
EOF

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Creating systemd service file..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Motionberry Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStartPre=/bin/bash -c 'touch $LOG_FILE && chown $USER_NAME:$USER_NAME $LOG_FILE && chmod 644 $LOG_FILE'
ExecStart=$APP_DIR/$PYTHON_ENV_DIR/bin/python $APP_DIR/run.py
StandardOutput=file:$LOG_FILE
StandardError=file:$LOG_FILE
Restart=always
User=$USER_NAME
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$APP_DIR/$PYTHON_ENV_DIR/bin"

[Install]
WantedBy=multi-user.target
EOF
else
    echo "Systemd service file already exists."
fi

echo "Reloading systemd, enabling, and starting the Motionberry service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Motionberry setup complete. Service status:"
sudo systemctl status "$SERVICE_NAME"
