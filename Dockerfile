FROM python:3.9-slim

# System dependencies for Containernet
RUN apt-get update && apt-get install -y \
    git build-essential sudo iproute2 iputils-ping netcat-openbsd net-tools curl \
    python3-setuptools python3-pip python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Install Containernet (Mininet fork that doesn’t need OVS kernel)
RUN git clone https://github.com/containernet/containernet.git /containernet && \
    cd /containernet && \
    util/install.sh -fnv

WORKDIR /app

# Copy project files
COPY controller ./controller
COPY tests ./tests
COPY requirements.txt .

# Python dependencies (including Ryu)
RUN pip install --no-cache-dir -r requirements.txt

# Optional non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 6653 8080

# Default command
CMD ["tail", "-f", "/dev/null"]
