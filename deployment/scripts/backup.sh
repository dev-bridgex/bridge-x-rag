#!/bin/bash

# Bridge-X-RAG Backup Script
# This script creates a backup of the MongoDB database

# Load environment variables
source src/.env

# Set backup directory
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/bridge_x_rag_${TIMESTAMP}.gz"

# Display banner
echo "====================================="
echo "  Bridge-X-RAG Backup Script"
echo "====================================="
echo "Backup file: $BACKUP_FILE"
echo

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup
echo "Creating database backup..."
docker exec -it mongodb mongodump \
    --uri="mongodb://${MONGODB_USERNAME}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}" \
    --gzip --archive=/tmp/temp_backup.gz

# Copy backup from container to host
echo "Copying backup to host..."
docker cp mongodb:/tmp/temp_backup.gz $BACKUP_FILE

# Clean up temporary backup in container
docker exec -it mongodb rm /tmp/temp_backup.gz

echo "Backup completed successfully!"
echo "Backup saved to: $BACKUP_FILE"
