#!/bin/bash
# Initial setup for RSS Aggregator

# Create data directory with correct permissions for container user (UID 1000)
mkdir -p data
if command -v docker &> /dev/null; then
    # If running on Linux, fix ownership for the container's non-root user
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Setting ownership of ./data to UID 1000 (container user)"
        sudo chown 1000:1000 data 2>/dev/null || echo "Warning: sudo required. Run: sudo chown 1000:1000 data"
    else
        # macOS/Windows – Docker uses a VM, permissions are usually fine
        echo "Detected non-Linux OS. Permissions for ./data should be handled by Docker."
    fi
else
    echo "Docker not found. Please install Docker and Docker Compose."
    exit 1
fi

# Copy environment example if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it and set a strong API_KEY."
fi

echo "Setup complete. Run 'docker compose up --build' to start."
