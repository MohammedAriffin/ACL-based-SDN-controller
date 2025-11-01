# Known-good Mininet base with OVS and tools
FROM iwaseyusuke/mininet

# Ensure Python3/pip and useful tools are present
RUN apt-get update && apt-get install -y \
    python3-pip python3-venv iputils-ping netcat-openbsd curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy your code
COPY controller ./controller
COPY tests ./tests
COPY requirements.txt .
COPY run_all.sh .

# Install Python deps (must include ryu)
RUN pip3 install --no-cache-dir -r requirements.txt

# Make entrypoint executable
RUN chmod +x run_all.sh

# Expose ports if you use Ryu REST as well
EXPOSE 6653 8080

# Mininet needs privileged; compose will set that
CMD ["./run_all.sh"]
