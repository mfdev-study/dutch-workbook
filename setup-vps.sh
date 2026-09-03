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

# Add cargo bin to PATH for current session
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Also add to bashrc for future sessions
for bashrc in /root/.bashrc /home/"$APP_USER"/.bashrc; do
    if [ -f "$bashrc" ]; then
        if ! grep -q '.local/bin\|.cargo/bin' "$bashrc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"' >> "$bashrc"
        fi
    fi
done

# Verify uv installation
if command -v uv &> /dev/null; then
    echo "uv installed successfully: $(uv --version)"
else
    echo "ERROR: uv installation failed"
    exit 1
fi

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
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd "$APP_DIR"
sudo -u "$APP_USER" bash -c "export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" && cd $APP_DIR && uv sync"

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
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
sudo -u "$APP_USER" bash -c "export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" && cd $APP_DIR && uv run python manage.py migrate --settings nederlandse_workbook.production_settings"
sudo -u "$APP_USER" bash -c "export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" && cd $APP_DIR && uv run python manage.py collectstatic --noinput --settings nederlandse_workbook.production_settings"

# Install systemd service
echo "Installing systemd service..."
cp "$APP_DIR/dutchworkbook.service" /etc/systemd/system/dutchworkbook.service
systemctl daemon-reload
systemctl enable dutchworkbook.service

# Install generation job processor (systemd timer)
echo "Installing generation job processor timer..."
cp "$APP_DIR/dutchworkbook-jobs.service" /etc/systemd/system/dutchworkbook-jobs.service
cp "$APP_DIR/dutchworkbook-jobs.timer" /etc/systemd/system/dutchworkbook-jobs.timer
systemctl daemon-reload
systemctl enable --now dutchworkbook-jobs.timer

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
