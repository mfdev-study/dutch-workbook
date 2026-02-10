#!/bin/bash
set -e

# Change to project directory
cd "$(dirname "$0")"

# Set production environment
export DJANGO_SETTINGS_MODULE="nederlandse_workbook.settings"
export PYTHONDONTWRITEBYTECODE=1
export DEBUG=0

echo "=== Dutch Workbook Production Server ==="

# Create logs directory
mkdir -p logs

# Install/verify dependencies
echo "Checking dependencies..."
uv sync --no-dev

# Run migrations
echo "Running database migrations..."
uv run python manage.py migrate --run-syncdb

# Create staticfiles directory (required for collectstatic)
mkdir -p staticfiles

# Collect static files
echo "Collecting static files..."
uv run python manage.py collectstatic --noinput 2>/dev/null || true

# Function to run backup on shutdown
backup_on_shutdown() {
    echo ""
    echo "[BACKUP] Running database backup before shutdown..."
    uv run python backup_db.py
    echo "[OK] Backup completed. Shutting down gracefully."
    exit 0
}

# Set up signal handlers for graceful shutdown
trap backup_on_shutdown SIGTERM SIGINT

# Load environment variables from .env if it exists
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start Gunicorn (not daemon mode so we can trap signals)
echo "Starting Gunicorn server on 127.0.0.1:8000..."
echo "Server started! Check logs/access.log for access logs."
echo "To stop gracefully (with backup): Ctrl+C"
exec uv run gunicorn nederlandse_workbook.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
