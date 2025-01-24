FROM debian:bookworm

RUN apt update && apt install -y --no-install-recommends \
        gosu \
        util-linux \
        ffmpeg \
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

RUN curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt update && apt install -y --no-install-recommends python3-picamera2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /motionberry

COPY . .

RUN python3 -m venv --system-site-packages .venv \
    && . .venv/bin/activate \
    && pip install --default-timeout=100 --upgrade pip \
    && pip install --default-timeout=100 .

RUN chmod +x /motionberry/entrypoint.sh

VOLUME ["/motionberry/config"]
VOLUME ["/motionberry/captures"]

EXPOSE 5000

ENTRYPOINT ["/motionberry/entrypoint.sh"]
CMD ["/motionberry/.venv/bin/python", "run.py"]

HEALTHCHECK --interval=60s --timeout=5s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1