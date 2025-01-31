#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR=".venv"
SERVICE_NAME="motionberry.service"
LOG_FILE="/var/log/motionberry.log"

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

echo "Creating log file and setting permissions..."
sudo touch "$LOG_FILE"
sudo chown $(whoami):$(whoami) "$LOG_FILE"
sudo chmod 644 "$LOG_FILE"

echo "Setting up log rotation for $LOG_FILE..."
sudo tee /etc/logrotate.d/motionberry > /dev/null <<EOF
$LOG_FILE {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 644 $(whoami) $(whoami)
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
ExecStart=$APP_DIR/$PYTHON_ENV_DIR/bin/python $APP_DIR/run.py >> $LOG_FILE 2>&1
Restart=always
User=$(whoami)
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
sudo systemctl start "$SERVICE_NAME"

echo "Motionberry setup complete. Service status:"
sudo systemctl status "$SERVICE_NAME"