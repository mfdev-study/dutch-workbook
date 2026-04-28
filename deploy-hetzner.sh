#!/bin/bash
# deploy-hetzner.sh - Deployment script for Hetzner VPS
# This script should be run on the VPS as the application user (dutchapp)

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/dutchworkbook"
BACKUP_DIR="/opt/dutchworkbook/backups"
SERVICE_NAME="dutchworkbook"
APP_USER="dutchapp"

# Print functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as correct user
check_user() {
    if [[ $EUID -eq 0 ]]; then
        print_error "Do not run this script as root. Run as '${APP_USER}' user."
        exit 1
    fi
    
    if [[ $(whoami) != "$APP_USER" ]]; then
        print_warning "Expected to run as '${APP_USER}', running as '$(whoami)'"
    fi
}

# Create backup before deployment
create_backup() {
    print_status "Creating backup before deployment..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre-deploy-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    tar -czf "$BACKUP_FILE" -C /opt dutchworkbook 2>/dev/null || true
    
    print_success "Backup created: $BACKUP_FILE"
}

# Pull latest changes
pull_changes() {
    print_status "Pulling latest changes from git..."
    
    cd "$APP_DIR"
    
    # Stash any local changes
    git stash push -m "Pre-deploy stash $(date)" 2>/dev/null || true
    
    # Pull latest changes
    git fetch origin
    git reset --hard origin/main
    
    print_success "Code updated successfully"
}

# Update dependencies
update_dependencies() {
    print_status "Updating Python dependencies..."
    
    cd "$APP_DIR"
    
    # Ensure UV is available
    if ! command -v uv &> /dev/null; then
        print_status "Installing UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    export PATH="$HOME/.cargo/bin:$PATH"
    uv sync
    
    print_success "Dependencies updated"
}

# Compile translations
compile_translations() {
    print_status "Compiling translations..."
    
    cd "$APP_DIR"
    export PATH="$HOME/.cargo/bin:$PATH"
    
    uv run python manage.py compilemessages --settings nederlandse_workbook.production_settings 2>&1 || print_warning "Translation compilation had issues"
    
    print_success "Translations compiled"
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    cd "$APP_DIR"
    export PATH="$HOME/.cargo/bin:$PATH"
    
    uv run python manage.py migrate --settings nederlandse_workbook.production_settings
    
    print_success "Migrations completed"
}

# Collect static files
collect_static() {
    print_status "Collecting static files..."
    
    cd "$APP_DIR"
    export PATH="$HOME/.cargo/bin:$PATH"
    
    uv run python manage.py collectstatic --noinput --settings nederlandse_workbook.production_settings
    
    print_success "Static files collected"
}

# Test application startup
test_startup() {
    print_status "Testing application startup..."
    
    cd "$APP_DIR"
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Quick check if the application can start
    timeout 10 uv run gunicorn --bind 127.0.0.1:9000 --workers 1 nederlandse_workbook.wsgi:application &
    GUNICORN_PID=$!
    sleep 3
    
    if kill -0 $GUNICORN_PID 2>/dev/null; then
        kill $GUNICORN_PID 2>/dev/null || true
        print_success "Application startup test passed"
    else
        print_error "Application failed to start"
        return 1
    fi
}

# Restart service
restart_service() {
    print_status "Restarting ${SERVICE_NAME} service..."
    
    sudo systemctl restart "$SERVICE_NAME"
    sleep 3
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service restarted successfully"
    else
        print_error "Service failed to start"
        sudo journalctl -u "$SERVICE_NAME" --no-pager -n 50
        return 1
    fi
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Get domain from production settings (basic extraction)
    DOMAIN=$(grep -oP "ALLOWED_HOSTS = \['\K[^']+" "$APP_DIR/nederlandse_workbook/production_settings.py" 2>/dev/null | head -1)
    
    if [[ -z "$DOMAIN" ]]; then
        DOMAIN="localhost"
    fi
    
    # Wait a bit for service to fully start
    sleep 5
    
    # Check if site responds
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/" 2>/dev/null || echo "000")
    
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        print_success "Health check passed (HTTP $HTTP_CODE)"
    else
        print_warning "Health check returned HTTP $HTTP_CODE"
    fi
}

# Print deployment summary
print_summary() {
    echo
    echo "=========================================="
    echo "         DEPLOYMENT SUMMARY"
    echo "=========================================="
    echo
    echo -e "${GREEN}✅ Deployment completed!${NC}"
    echo
    echo "📊 Status:"
    echo "   - Service: $(systemctl is-active $SERVICE_NAME)"
    echo "   - Nginx: $(systemctl is-active nginx)"
    echo "   - PostgreSQL: $(systemctl is-active postgresql)"
    echo
    echo "🔧 Quick Commands:"
    echo "   - View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "   - Restart: sudo systemctl restart $SERVICE_NAME"
    echo "   - Check status: sudo systemctl status $SERVICE_NAME"
    echo
}

# Main deployment flow
main() {
    echo "=========================================="
    echo "  DUTCH WORKBOOK DEPLOYMENT"
    echo "=========================================="
    echo
    
    check_user
    create_backup
    pull_changes
    update_dependencies
    compile_translations
    run_migrations
    collect_static
    
    # Test startup before restarting service
    if test_startup; then
        restart_service
        health_check
        print_summary
    else
        print_error "Deployment aborted due to startup test failure"
        exit 1
    fi
}

# Error handling
trap 'print_error "Deployment failed at line $LINENO"' ERR

# Run deployment
main "$@"
