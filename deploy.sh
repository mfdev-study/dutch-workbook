#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Get domain from user
get_domain() {
    while true; do
        echo -n "Please enter your domain name (e.g., example.com): "
        read -r DOMAIN
        
        if [[ -z "$DOMAIN" ]]; then
            print_error "Domain name cannot be empty."
            continue
        fi
        
        # Basic domain validation
        if [[ $DOMAIN =~ ^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
            break
        else
            print_error "Invalid domain name format. Please enter a valid domain (e.g., example.com)."
        fi
    done
    
    export DOMAIN
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "Please do not run this script as root. Run it as a regular user with sudo privileges."
        exit 1
    fi
}

# Detect OS and package manager
detect_os() {
    if [[ -f /etc/debian_version ]]; then
        OS="debian"
        PKG_MANAGER="apt"
        print_status "Detected Debian/Ubuntu system"
    elif [[ -f /etc/redhat-release ]]; then
        OS="redhat"
        PKG_MANAGER="yum"
        print_status "Detected Red Hat/CentOS system"
    else
        print_error "Unsupported operating system. This script supports Debian/Ubuntu and Red Hat/CentOS."
        exit 1
    fi
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    if [[ $PKG_MANAGER == "apt" ]]; then
        sudo apt update && sudo apt upgrade -y
    else
        sudo yum update -y
    fi
    print_success "System updated"
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    if [[ $PKG_MANAGER == "apt" ]]; then
        sudo apt install -y software-properties-common curl wget git \
            python3 python3-pip python3-venv nginx certbot python3-certbot-nginx \
            postgresql postgresql-contrib build-essential
    else
        sudo yum install -y curl wget git python3 python3-pip \
            nginx certbot python3-certbot-nginx postgresql-server postgresql-contrib \
            gcc gcc-c++ make
    fi
    
    print_success "Dependencies installed"
}

# Create application user
create_app_user() {
    print_status "Creating application user..."
    
    if ! id "dutchapp" &>/dev/null; then
        sudo useradd -m -s /bin/bash dutchapp
        print_success "User 'dutchapp' created"
    else
        print_warning "User 'dutchapp' already exists"
    fi
}

# Setup PostgreSQL database
setup_database() {
    print_status "Setting up PostgreSQL database..."
    
    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE dutchworkbook;" || print_warning "Database may already exist"
    sudo -u postgres psql -c "CREATE USER dutchapp WITH PASSWORD 'secure_password_123';" || print_warning "User may already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dutchworkbook TO dutchapp;" || print_warning "Privileges may already be granted"
    
    print_success "PostgreSQL database setup complete"
}

# Clone and setup application
setup_application() {
    print_status "Setting up application..."
    
    # Create application directory
    sudo mkdir -p /opt/dutchworkbook
    sudo chown dutchapp:dutchapp /opt/dutchworkbook
    
    # Copy application files (assuming current directory is the project)
    print_status "Copying application files..."
    sudo cp -r /home/mik/Projects/nederlandse-workbook/* /opt/dutchworkbook/
    sudo chown -R dutchapp:dutchapp /opt/dutchworkbook
    
    # Switch to application user for remaining setup
    sudo -u dutchapp bash << 'EOF'
cd /opt/dutchworkbook

# Install UV if not present
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install Python dependencies
export PATH="$HOME/.cargo/bin:$PATH"
uv sync

# Create production settings file
cat > nederlandse_workbook/production_settings.py << 'EOS'
import os
from .settings import *

# SECURITY SETTINGS
DEBUG = False
ALLOWED_HOSTS = ['${DOMAIN}', 'www.${DOMAIN}', 'localhost', '127.0.0.1']
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dutchworkbook',
        'USER': 'dutchapp',
        'PASSWORD': 'secure_password_123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# STATIC FILES
STATIC_ROOT = '/opt/dutchworkbook/staticfiles'
STATIC_URL = '/static/'

# MEDIA FILES (if any)
MEDIA_ROOT = '/opt/dutchworkbook/media'
MEDIA_URL = '/media/'

# SECURITY
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/opt/dutchworkbook/django.log',
        },
    },
    'root': {
        'handlers': ['file'],
    },
}
EOS

# Replace DOMAIN placeholder
sed -i "s/\${DOMAIN}/${DOMAIN}/g" nederlandse_workbook/production_settings.py

# Collect static files
export PATH="$HOME/.cargo/bin:$PATH"
uv run python manage.py collectstatic --noinput --settings nederlandse_workbook.production_settings

# Run migrations
uv run python manage.py migrate --settings nederlandse_workbook.production_settings

# Create superuser (optional)
echo "Creating superuser (optional - press Ctrl+C to skip)"
uv run python manage.py createsuperuser --settings nederlandse_workbook.production_settings || echo "Superuser creation skipped"

EOF
    
    print_success "Application setup complete"
}

# Setup Gunicorn service
setup_gunicorn() {
    print_status "Setting up Gunicorn service..."
    
    sudo tee /etc/systemd/system/dutchworkbook.service > /dev/null << EOF
[Unit]
Description=Dutch Workbook Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=dutchapp
Group=dutchapp
WorkingDirectory=/opt/dutchworkbook
Environment=PATH=/opt/dutchworkbook/.venv/bin
Environment=DJANGO_SETTINGS_MODULE=nederlandse_workbook.production_settings
ExecStart=/opt/dutchworkbook/.venv/bin/gunicorn --bind 127.0.0.1:8000 nederlandse_workbook.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
Timeout=30

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and start service
    sudo systemctl daemon-reload
    sudo systemctl enable dutchworkbook
    sudo systemctl start dutchworkbook
    
    print_success "Gunicorn service started"
}

# Setup Nginx and SSL
setup_nginx_ssl() {
    print_status "Setting up Nginx and SSL certificate..."
    
    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/dutchworkbook > /dev/null << EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};
    
    # Redirect to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};
    
    # SSL configuration (will be completed by certbot)
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Application
    location /static/ {
        alias /opt/dutchworkbook/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/dutchworkbook/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
EOF
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/dutchworkbook /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    sudo nginx -t
    
    # Setup SSL with Let's Encrypt
    print_status "Requesting SSL certificate from Let's Encrypt..."
    sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN} --redirect
    
    # Setup certbot auto-renewal
    sudo crontab -l | grep -q "certbot renew" || (sudo crontab -l; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
    
    # Restart Nginx
    sudo systemctl restart nginx
    
    print_success "Nginx and SSL setup complete"
}

# Setup firewall
setup_firewall() {
    print_status "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian
        sudo ufw allow ssh
        sudo ufw allow 'Nginx Full'
        sudo ufw --force enable
        print_success "UFW firewall configured"
    elif command -v firewall-cmd &> /dev/null; then
        # Red Hat/CentOS
        sudo firewall-cmd --permanent --add-service=ssh
        sudo firewall-cmd --permanent --add-service=http
        sudo firewall-cmd --permanent --add-service=https
        sudo firewall-cmd --reload
        print_success "Firewalld configured"
    else
        print_warning "No supported firewall found. Please manually configure your firewall."
    fi
}

# Create backup script
setup_backup() {
    print_status "Setting up backup script..."
    
    sudo tee /opt/dutchworkbook/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/dutchworkbook/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U dutchapp -d dutchworkbook > $BACKUP_DIR/db_backup_$DATE.sql

# Media files backup (if any)
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C /opt/dutchworkbook media/ 2>/dev/null || true

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF
    
    sudo chmod +x /opt/dutchworkbook/backup.sh
    sudo chown dutchapp:dutchapp /opt/dutchworkbook/backup.sh
    
    # Add to crontab for daily backups
    sudo crontab -l | grep -q "backup.sh" || (sudo crontab -l; echo "0 2 * * * /opt/dutchworkbook/backup.sh") | sudo crontab -
    
    print_success "Backup script configured"
}

# Create monitoring script
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    sudo tee /opt/dutchworkbook/healthcheck.sh > /dev/null << 'EOF'
#!/bin/bash
# Simple health check for the application
APP_URL="https://${DOMAIN}"
LOG_FILE="/opt/dutchworkbook/health.log"

# Check if the application is responding
if curl -f -s $APP_URL > /dev/null; then
    echo "$(date): Application is healthy" >> $LOG_FILE
else
    echo "$(date): Application is DOWN - restarting service" >> $LOG_FILE
    sudo systemctl restart dutchworkbook
fi
EOF
    
    # Replace DOMAIN placeholder
    sudo sed -i "s/\${DOMAIN}/${DOMAIN}/g" /opt/dutchworkbook/healthcheck.sh
    
    sudo chmod +x /opt/dutchworkbook/healthcheck.sh
    sudo chown dutchapp:dutchapp /opt/dutchworkbook/healthcheck.sh
    
    # Add to crontab for health checks every 5 minutes
    sudo crontab -l | grep -q "healthcheck.sh" || (sudo crontab -l; echo "*/5 * * * * /opt/dutchworkbook/healthcheck.sh") | sudo crontab -
    
    print_success "Monitoring setup complete"
}

# Print deployment summary
print_summary() {
    echo
    echo "=========================================="
    echo "         DEPLOYMENT SUMMARY"
    echo "=========================================="
    echo
    echo -e "${GREEN}✅ Your Dutch Workbook is now deployed!${NC}"
    echo
    echo "📍 Application URL: https://${DOMAIN}"
    echo "📍 Admin URL: https://${DOMAIN}/admin/"
    echo
    echo "🔧 Service Status:"
    echo "   - Gunicorn: $(systemctl is-active dutchworkbook)"
    echo "   - Nginx: $(systemctl is-active nginx)"
    echo "   - PostgreSQL: $(systemctl is-active postgresql)"
    echo
    echo "📁 Important Paths:"
    echo "   - Application: /opt/dutchworkbook/"
    echo "   - Config: /opt/dutchworkbook/nederlandse_workbook/production_settings.py"
    echo "   - Logs: /opt/dutchworkbook/django.log"
    echo "   - Backups: /opt/dutchworkbook/backups/"
    echo
    echo "🔧 Management Commands:"
    echo "   - Restart app: sudo systemctl restart dutchworkbook"
    echo "   - View logs: sudo journalctl -u dutchworkbook -f"
    echo "   - Nginx config: sudo nginx -t && sudo systemctl reload nginx"
    echo "   - Run migrations: cd /opt/dutchworkbook && sudo -u dutchapp uv run python manage.py migrate --settings nederlandse_workbook.production_settings"
    echo
    echo "🔒 SSL Certificate:"
    echo "   - Auto-renewal is configured via certbot"
    echo "   - Certificate location: /etc/letsencrypt/live/${DOMAIN}/"
    echo
    echo "💡 Next Steps:"
    echo "   1. Visit https://${DOMAIN}/admin/ to configure your site"
    echo "   2. Create some categories and add words"
    echo "   3. Test the flashcard and quiz features"
    echo "   4. Check logs if any issues occur"
    echo
    echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
    echo "   - Change the PostgreSQL password in production_settings.py"
    echo "   - Consider setting up fail2ban for additional security"
    echo "   - Regularly check for system updates"
    echo "   - Monitor your application logs"
    echo
}

# Main deployment function
main() {
    echo "=========================================="
    echo "  DUTCH WORKBOOK DEPLOYMENT SCRIPT"
    echo "=========================================="
    echo
    
    print_status "This script will deploy your Dutch Workbook to production with HTTPS."
    print_status "Please ensure you have sudo privileges on this server."
    echo
    
    get_domain
    check_root
    detect_os
    
    print_status "Starting deployment for domain: ${DOMAIN}"
    echo
    
    update_system
    install_dependencies
    create_app_user
    setup_database
    setup_application
    setup_gunicorn
    setup_nginx_ssl
    setup_firewall
    setup_backup
    setup_monitoring
    
    print_summary
}

# Error handling
trap 'print_error "Deployment failed at line $LINENO"' ERR

# Run the deployment
main "$@"