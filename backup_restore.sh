#!/bin/env bash
set -e

VOLUME_NAME="rss-aggregator_data_volume"

case $1 in
    backup)
        BACKUP_DIR=${2:-./backups}
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/aggregator_$(date +%Y%m%d_%H%M%S).db"
        echo "Creating backup of $VOLUME_NAME ..."
        docker run --rm -v "$VOLUME_NAME":/data -v "$BACKUP_DIR":/backup alpine cp /data/aggregator.db "/backup/$(basename "$BACKUP_FILE")"
        echo "Backup saved to $BACKUP_FILE"
        ;;
    restore)
        BACKUP_FILE="$2"
        if [ -z "$BACKUP_FILE" ]; then
            echo "Usage: $0 restore /path/to/backup.db"
            exit 1
        fi
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "Backup file not found: $BACKUP_FILE"
            echo "Available backups:"
            find ./backups -maxdepth 1 -name "aggregator_*.db" -type f 2>/dev/null || echo "No backups found in ./backups"
            exit 1
        fi
        echo "Restoring from $BACKUP_FILE to $VOLUME_NAME ..."
        docker compose down
        BACKUP_DIR=$(dirname "$BACKUP_FILE")
        docker run --rm -v "$VOLUME_NAME":/data -v "$BACKUP_DIR":/backup alpine cp "/backup/$(basename "$BACKUP_FILE")" /data/aggregator.db
        docker compose up -d
        echo "Restore complete. Container restarted."
        ;;
    *)
        echo "Usage: $0 {backup|restore} [args]"
        echo "  backup [backup_dir]                 default backup_dir = ./backups"
        echo "  restore /path/to/backup.db"
        exit 1
        ;;
esac