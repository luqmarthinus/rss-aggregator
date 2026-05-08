#!/usr/bin/env bash
set -Eeuo pipefail

echo "[+] Initialising RSS Aggregator setup..."

# ------------------------------------------------------------------------------
# Check Docker
# ------------------------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
    echo "[-] Docker not found. Please install Docker and Docker Compose."
    exit 1
fi

mkdir -p data

# ------------------------------------------------------------------------------
# Handle permissions safely (only if explicitly required)
# ------------------------------------------------------------------------------

OS="$(uname -s)"

if [[ "$OS" == "Linux" ]]; then
    echo "[+] Linux detected"

    # Only attempt chown if user explicitly has sudo
    if command -v sudo >/dev/null 2>&1; then
        echo "[+] Setting ownership for container UID 1001"
        sudo chown 1001:1001 data || {
            echo "[!] Could not set ownership. Run manually:"
            echo "    sudo chown 1001:1001 data"
        }
    else
        echo "[!] sudo not available. Skipping ownership change."
    fi
else
    echo "[+] Non-Linux OS detected ($OS). Skipping chown."
fi

# ------------------------------------------------------------------------------
# Env file bootstrap
# ------------------------------------------------------------------------------

if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "[+] Created .env from .env.example"
        echo "[!] IMPORTANT: Set a strong API_KEY before running."
    else
        echo "[-] Missing .env.example. Cannot continue safely."
        exit 1
    fi
else
    echo "[+] .env already exists"
fi

echo ""
echo "[✓] Setup complete"
echo "    Next: docker compose up --build"