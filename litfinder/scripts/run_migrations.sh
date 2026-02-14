#!/bin/bash
# Run Alembic migrations inside Docker container

set -e

echo "🔄 Running database migrations..."

# Check if database container is running
if ! docker ps | grep -q litfinder_db; then
    echo "❌ Database container is not running. Start it with: docker compose up db"
    exit 1
fi

# Check if API container is running
if ! docker ps | grep -q litfinder.*api; then
    echo "❌ API container is not running. Start it with: docker compose up api"
    exit 1
fi

# Wait for database to be ready with active polling
echo "⏳ Waiting for database to be ready..."

MAX_RETRIES=30
RETRY_COUNT=0
RETRY_DELAY=1

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))

    # Check if database is ready using pg_isready
    if docker compose exec -T db pg_isready -U postgres -d postgres > /dev/null 2>&1; then
        echo "✓ Database is ready (attempt $RETRY_COUNT/$MAX_RETRIES)"
        break
    fi

    # Database not ready yet
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ Database failed to become ready after $MAX_RETRIES attempts"
        echo "   This may indicate a database startup issue or connection problem"
        exit 1
    fi

    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES: Database not ready, retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY

    # Exponential backoff with max delay of 5 seconds
    RETRY_DELAY=$((RETRY_DELAY * 2))
    if [ $RETRY_DELAY -gt 5 ]; then
        RETRY_DELAY=5
    fi
done

# Run migrations (use -T flag to disable pseudo-TTY for CI/CD)
docker compose exec -T api alembic upgrade head

echo "✅ Migrations completed successfully!"
