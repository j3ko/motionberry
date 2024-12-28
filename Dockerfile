FROM debian:bookworm

# Install system dependencies and build tools
RUN apt update && apt install -y --no-install-recommends \
        gosu \
        build-essential \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-numpy \
        python3-setuptools \
        curl \
        gnupg \
        libcap-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi repository
RUN curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages and clean up
RUN apt update && apt install -y --no-install-recommends python3-picamera2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
   
# Set the working directory
WORKDIR /motionberry

# Copy the application code into the container
COPY . .

# Create and activate a virtual environment
RUN python3 -m venv --system-site-packages .venv \
    && . .venv/bin/activate \
    && pip install --default-timeout=100 --upgrade pip \
    && pip install --default-timeout=100 --no-cache-dir -r requirements.txt

RUN chmod +x /motionberry/entrypoint.sh

VOLUME ["/motionberry/config"]
VOLUME ["/motionberry/captures"]

EXPOSE 5000

ENTRYPOINT ["/motionberry/entrypoint.sh"]
CMD ["/motionberry/.venv/bin/python", "run.py"]
