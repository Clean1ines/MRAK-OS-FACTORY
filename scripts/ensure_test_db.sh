#!/bin/bash
# Automatically start PostgreSQL test database if not running

CONTAINER_NAME="mrak-postgres-test"
DB_PORT="5433"
DB_USER="test"
DB_PASSWORD="test123"
DB_NAME="mrak_test"

# Check if port is already in use (container running)
if netstat -tlnp 2>/dev/null | grep -q ":${DB_PORT}" || ss -tlnp 2>/dev/null | grep -q ":${DB_PORT}"; then
    echo "✅ PostgreSQL already running on port ${DB_PORT}"
    exit 0
fi

# Check if container exists but stopped
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🔄 Starting existing container..."
    docker start "${CONTAINER_NAME}"
else
    echo "🐳 Creating new PostgreSQL container..."
    docker run -d \
        --name "${CONTAINER_NAME}" \
        -e POSTGRES_USER="${DB_USER}" \
        -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
        -e POSTGRES_DB="${DB_NAME}" \
        -p "${DB_PORT}:5432" \
        pgvector/pgvector:pg15
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        exit 0
    fi
    sleep 1
done

echo "❌ PostgreSQL failed to start"
exit 1
