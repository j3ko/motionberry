FROM debian:bookworm

# Install base dependencies
RUN apt update && apt install -y --no-install-recommends \
        gosu \
        sudo \
        curl \
        gnupg \
        libcap-dev \
        lsb-release \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi repository
RUN curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up motionberry
WORKDIR /motionberry
COPY . .

# Make install.sh executable and run it with --no-service
RUN chmod +x /motionberry/scripts/install.sh \
    && bash /motionberry/scripts/install.sh --no-service

# Make entrypoint script executable
RUN chmod +x /motionberry/entrypoint.sh

# Define volumes and expose port
VOLUME ["/motionberry/config"]
VOLUME ["/motionberry/captures"]
EXPOSE 5000

# Set entrypoint and default command
ENTRYPOINT ["/motionberry/entrypoint.sh"]
CMD ["/motionberry/.venv/bin/python", "run.py"]

# Health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1