#!/bin/bash
# Usage: ./backup_restore.sh backup <database_path> [backup_dir]
#        ./backup_restore.sh restore <backup_file> <database_path>

set -e
COMMAND=$1
case $COMMAND in
    backup)
        DB_PATH=${2:-./data/aggregator.db}
        BACKUP_DIR=${3:-./backups}
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/feeds_$(date +%Y%m%d_%H%M%S).db"
        sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
        echo "Backup saved to $BACKUP_FILE"
        ;;
    restore)
        BACKUP_FILE=$2
        DB_PATH=$3
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "Backup file not found: $BACKUP_FILE"
            exit 1
        fi
        cp "$BACKUP_FILE" "$DB_PATH"
        echo "Restored $BACKUP_FILE to $DB_PATH"
        ;;
    *)
        echo "Usage: $0 {backup|restore} [args]"
        exit 1
        ;;
esac
