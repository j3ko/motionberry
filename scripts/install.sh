#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
APP_DIR=$(realpath "$SCRIPT_DIR/..")
PYTHON_ENV_DIR=".venv"
SERVICE_NAME="motionberry.service"
LOG_FILE="/var/log/motionberry.log"
USER_NAME=${SUDO_USER:-$(whoami)}

# Parse command-line arguments
SKIP_SERVICE=false
for arg in "$@"; do
    case $arg in
        --no-service)
            SKIP_SERVICE=true
            shift
            ;;
        *)
            echo "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# Detect OS version
OS_VERSION=$(lsb_release -cs)

echo "Installing required libraries..."
sudo apt update
sudo apt install -y --no-install-recommends \
    util-linux \
    mkvtoolnix \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-numpy \
    python3-picamera2

# Install GPAC from source if OS is Bookworm
if [ "$OS_VERSION" = "bookworm" ] || [ "$OS_VERSION" = "trixie" ]; then
    echo "Detected Debian Bookworm. Building GPAC from source..."
    sudo apt install -y --no-install-recommends build-essential cmake

    sudo apt install -y --no-install-recommends \
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
        mesa-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

    echo "Building GPAC..."
    cd /tmp
    git clone https://github.com/gpac/gpac.git
    cd gpac
    ./configure --static-bin --use-zlib=no
    make -j$(nproc)
    sudo make install
    make clean
    cd ..
    rm -rf gpac
    cd "$APP_DIR"
else
    echo "Installing GPAC from package..."
    sudo apt install -y --no-install-recommends gpac
fi

echo "Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv --system-site-packages "$PYTHON_ENV_DIR"
. "$PYTHON_ENV_DIR/bin/activate"
pip install --default-timeout=100 --upgrade pip
pip install --default-timeout=100 .

# Skip logging and systemd service setup if --no-service flag is provided
if [ "$SKIP_SERVICE" = false ]; then
    echo "Creating log file and setting permissions..."
    sudo touch "$LOG_FILE"
    sudo chown "$USER_NAME":"$USER_NAME" "$LOG_FILE"
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
    create 644 $USER_NAME $USER_NAME
    copytruncate
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
ExecStart=$APP_DIR/$PYTHON_ENV_DIR/bin/python $APP_DIR/run.py
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
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
    sudo systemctl restart "$SERVICE_NAME" & disown

    echo "Motionberry setup complete. Service status:"
    sudo systemctl status "$SERVICE_NAME"
else
    echo "Skipping logging and systemd service setup (--no-service flag provided)."
fi