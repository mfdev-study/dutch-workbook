.PHONY: help setup migrate test lint format clean translate

help:
	@echo "Dutch Workbook - Available commands:"
	@echo "  setup      - Set up development environment"
	@echo "  migrate    - Run database migrations"
	@echo "  test       - Run all tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  lint       - Run code linting (ruff)"
	@echo "  format     - Format code (ruff)"
	@echo "  clean      - Clean up cache and temporary files"
	@echo "  translate  - Compile translation files"
	@echo "  shell      - Open Django shell"
	@echo "  runserver  - Run development server"

setup:
	@echo "Setting up development environment..."
	uv sync
	uv run python manage.py migrate --settings=nederlandse_workbook.settings
	@echo "Setup complete!"

migrate:
	uv run python manage.py migrate --settings=nederlandse_workbook.settings

test:
	uv run python manage.py test --settings=nederlandse_workbook.settings --verbosity=2

test-coverage:
	uv run coverage run manage.py test --settings=nederlandse_workbook.settings
	uv run coverage report
	uv run coverage html

lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/
	@echo "Cleanup complete!"

translate:
	@echo "Compiling translation files..."
	uv run python manage.py compilemessages --settings=nederlandse_workbook.settings
	@echo "Translations compiled!"

shell:
	uv run python manage.py shell --settings=nederlandse_workbook.settings

runserver:
	uv run python manage.py runserver --settings=nederlandse_workbook.settings

createsuperuser:
	uv run python manage.py createsuperuser --settings=nederlandse_workbook.settings

# Deployment commands
deploy:
	@echo "Deploying to production..."
	ssh dutchapp@your-server "cd /opt/dutchworkbook && ./deploy-hetzner.sh"
	@echo "Deployment complete!"

# Database backup
backup:
	@echo "Creating database backup..."
	pg_dump -h localhost -U dutchapp dutchworkbook > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup complete!"
