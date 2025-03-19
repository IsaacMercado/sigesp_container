#!/bin/bash

DB_NAME=$1

if [ -z "$DB_NAME" ]; then
  echo "Error: You must provide a database name as a parameter"
  exit 1
fi

CONTAINER_NAME="sigesp-v2"
DATE=$(date +"%Y%m%d%H%M")

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
BACKUP_DIR="$SCRIPT_DIR/backups"

mkdir -p $BACKUP_DIR

docker exec -t $CONTAINER_NAME su -c "pg_dump $DB_NAME" postgres > $BACKUP_DIR/backup_$DATE.sql

gzip $BACKUP_DIR/backup_$DATE.sql

find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +7 -exec rm {} \;

echo "Backup completed: $BACKUP_DIR/backup_$DATE.sql.gz"
