#!/bin/bash
set -e

cd "$(dirname "$0")"

export DJANGO_SETTINGS_MODULE="nederlandse_workbook.settings"
export PYTHONDONTWRITEBYTECODE=1

echo "=== Dutch Workbook Dev Server ==="

if [[ ! -d .venv ]]; then
    echo "Setting up virtual environment..."
    uv sync
fi

echo "Running migrations..."
uv run python manage.py migrate

echo "Starting dev server on http://127.0.0.1:8000"
echo "Quit with Ctrl+C"
exec uv run python manage.py runserver 0.0.0.0:8000
