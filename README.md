# Motionberry

Motion detection and streaming solution for Raspberry Pi, built using `picamera2`.

## Pre-requisites

- A Raspberry Pi
- A camera module compatible with picamera2 (e.g., Raspberry Pi Camera Module 3).

## Docker installation
Run the following command to deploy Motionberry using Docker:
```bash
docker run --name motionberry \
  --privileged \
  -e PUID 1000 \
  -e PGID 1000 \
  -v <path to config.yml>:/motionberry/config \
  -v <path to capture directory>:/motionberry/captures \
  -v /run/udev:/run/udev:ro \
  -p 5000:5000 \
  j3ko/motionberry:latest
```

Explanation of Options:

- `--privileged`: Required for hardware access, such as the camera module.
- `-e PUID` / `-e PGID`: Set user and group IDs to match your system's user permissions.
- `-v <path>`: Map local directories to container paths:
  - `<path to config.yml>`: Path to your configuration file.
  - `<path to capture directory>`: Directory where captures will be stored.
- `-p 5000:5000`: Maps port 5000 on the host to the container.

Replace `<path to config.yml>` and `<path to capture directory>` with appropriate paths on your host machine.

## Bare metal installation
To install and run Motionberry natively on your Raspberry Pi, follow these steps:
1. Install Required Libraries:
   ```bash
   sudo apt install -y --no-install-recommends \
    git \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-numpy \
    python3-picamera2
   ```
1. Clone the Repository:
   ```bash
   git clone https://github.com/j3ko/motionberry.git
   ```
1. Set Up a Virtual Environment:
   ```
   cd motionberry
   python3 -m venv --system-site-packages .venv
   . .venv/bin/activate
   pip install --upgrade pip
   pip install --no-cache-dir -r requirements.txt
   ```
1. Run the Application:
   ```bash
   .venv/bin/python run.py
   ```

# Configuration

WIP