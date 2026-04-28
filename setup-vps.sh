#!/bin/bash
# Initial setup script for Hetzner VPS
# Run this manually on the VPS as root or with sudo

set -e

echo "=== Dutch Workbook VPS Setup ==="

# Configuration
APP_DIR="/opt/dutchworkbook"
APP_USER="dutchapp"
REPO_URL="git@github.com:mfdev-study/dutch-workbook.git"

# Create application user if not exists
if ! id "$APP_USER" &>/dev/null; then
    echo "Creating user: $APP_USER"
    useradd -m -s /bin/bash "$APP_USER"
else
    echo "User $APP_USER already exists"
fi

# Install dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip git curl

# Install uv
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Clone repository
if [ ! -d "$APP_DIR" ]; then
    echo "Cloning repository to $APP_DIR..."
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
else
    echo "Directory $APP_DIR already exists"
fi

# Setup Python environment
echo "Setting up Python environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" bash -c "export PATH=\"$HOME/.cargo/bin:$PATH\" && uv sync"

# Create production settings if not exists
if [ ! -f "$APP_DIR/nederlandse_workbook/production_settings.py" ]; then
    echo "Creating production settings..."
    cat > "$APP_DIR/nederlandse_workbook/production_settings.py" <<'EOF'
from .settings import *

# Production settings
DEBUG = False
SECRET_KEY = 'CHANGE_THIS_TO_A_SECURE_SECRET_KEY'

# Database (SQLite by default, uncomment PostgreSQL if needed)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'dutchworkbook',
#         'USER': 'dutchapp',
#         'PASSWORD': 'CHANGE_THIS_PASSWORD',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Allowed hosts
ALLOWED_HOSTS = ['*']  # Change to your domain

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
EOF'
    chown "$APP_USER:$APP_USER" "$APP_DIR/nederlandse_workbook/production_settings.py"
fi

# Run initial setup
echo "Running initial Django setup..."
sudo -u "$APP_USER" bash -c "cd $APP_DIR && export PATH=\"$HOME/.cargo/bin:$PATH\" && uv run python manage.py migrate --settings nederlandse_workbook.production_settings"
sudo -u "$APP_USER" bash -c "cd $APP_DIR && export PATH=\"$HOME/.cargo/bin:$PATH\" && uv run python manage.py collectstatic --noinput --settings nederlandse_workbook.production_settings"

# Install systemd service
echo "Installing systemd service..."
cp "$APP_DIR/dutchworkbook.service" /etc/systemd/system/dutchworkbook.service"
systemctl daemon-reload
systemctl enable dutchworkbook.service

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Edit $APP_DIR/nederlandse_workbook/production_settings.py"
echo "2. Set a secure SECRET_KEY"
echo "3. Configure ALLOWED_HOSTS with your domain"
echo "4. Optionally configure PostgreSQL"
echo "5. Start the service: systemctl start dutchworkbook"
echo "6. Check status: systemctl status dutchworkbook"
echo ""
echo "To start the application:"
echo "  systemctl start dutchworkbook"
