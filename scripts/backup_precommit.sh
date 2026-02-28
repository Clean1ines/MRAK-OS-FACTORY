#!/bin/bash
# Pre-commit hook: create a database backup before each commit

# Load environment variables from .env if present (optional)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set. Cannot create backup."
    exit 1
fi

# Ensure backup directory exists
mkdir -p backups

# Create backup
echo "Creating database backup: backups/latest.sql"
pg_dump "$DATABASE_URL" > backups/latest.sql

if [ $? -eq 0 ]; then
    echo "Backup completed successfully."
    exit 0
else
    echo "Backup failed!"
    exit 1
fi
