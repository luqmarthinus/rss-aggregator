#!/usr/bin/env bash

set -Eeuo pipefail

VOLUME_NAME="rss_aggregator_data"
BACKUP_DIR_DEFAULT="./backups"

usage() {
    cat <<EOF
Usage:
  $0 backup [backup_dir]
  $0 restore /path/to/backup.db
EOF
}

backup_db() {
    local backup_dir="${1:-$BACKUP_DIR_DEFAULT}"

    mkdir -p "$backup_dir"

    local backup_file
    backup_file="$backup_dir/aggregator_$(date +%Y%m%d_%H%M%S).db"

    echo "[+] Creating SQLite backup..."

    docker run --rm \
        -v "${VOLUME_NAME}:/data" \
        -v "$(realpath "$backup_dir"):/backup" \
        alpine sh -c "
            apk add --no-cache sqlite >/dev/null &&
            sqlite3 /data/aggregator.db '.backup /backup/$(basename "$backup_file")'
        "

    echo "[+] Backup saved to: $backup_file"
}

restore_db() {
    local backup_file="$1"

    if [[ -z "${backup_file:-}" ]]; then
        echo "[-] Missing backup file"
        usage
        exit 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        echo "[-] Backup file not found: $backup_file"
        exit 1
    fi

    echo "[+] Stopping containers..."
    docker compose down

    echo "[+] Restoring database..."

    docker run --rm \
        -v "${VOLUME_NAME}:/data" \
        -v "$(dirname "$(realpath "$backup_file")"):/backup" \
        --user root \
        alpine sh -c "
            cp /backup/$(basename "$backup_file") /data/aggregator.db &&
            chown 1001:1001 /data/aggregator.db &&
            chmod 600 /data/aggregator.db
        "

    echo "[+] Starting containers..."
    docker compose up -d

    echo "[+] Restore complete."
}

case "${1:-}" in
    backup)
        backup_db "${2:-}"
        ;;
    restore)
        restore_db "${2:-}"
        ;;
    *)
        usage
        exit 1
        ;;
esac