#!/bin/bash
# Start Agent Bus containers and show live logs
# Usage: ./scripts/start-live.sh [service...]
# Examples:
#   ./scripts/start-live.sh          # All main services
#   ./scripts/start-live.sh api      # Only API logs
#   ./scripts/start-live.sh api orchestrator  # API and orchestrator logs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Default services to tail
DEFAULT_SERVICES="api worker orchestrator"

# Use provided services or defaults
SERVICES="${@:-$DEFAULT_SERVICES}"

echo "Starting Agent Bus containers..."
docker compose up -d

echo ""
echo "Waiting for services to be healthy..."
echo ""

# Wait for API to be ready (depends on postgres and redis)
MAX_WAIT=60
WAIT_COUNT=0
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo "Timeout waiting for API to be healthy"
        echo "Check logs with: docker compose logs api"
        exit 1
    fi
    echo -n "."
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

echo ""
echo "Services are healthy!"
echo ""
echo "=========================================="
echo "  Agent Bus is running"
echo "=========================================="
echo "  API:        http://localhost:8000"
echo "  Swagger UI: http://localhost:8000/docs"
echo "  Health:     http://localhost:8000/health"
echo "=========================================="
echo ""
echo "Showing live logs for: $SERVICES"
echo "(Press Ctrl+C to stop viewing logs - containers will keep running)"
echo ""

# Tail logs from specified services
docker compose logs -f $SERVICES
