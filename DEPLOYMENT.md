# Deployment Guide - Dutch Workbook to Hetzner VPS

This guide explains how to set up CI/CD for automatic deployment to a Hetzner VPS.

## Prerequisites

- Hetzner VPS with:
  - Ubuntu/Debian operating system
  - User `dutchapp` created (or your preferred app user)
  - Application deployed at `/opt/dutchworkbook`
  - Systemd service `dutchworkbook` configured
  - Nginx installed and configured
  - PostgreSQL database set up **(optional)** - the app defaults to SQLite; to use
    PostgreSQL instead, provision a database and set `DB_ENGINE`/`DB_*` env vars
  - Git repository cloned at `/opt/dutchworkbook`

## Step 1: Configure GitHub Secrets

Navigate to your GitHub repository and go to **Settings → Secrets and variables → Actions → New repository secret**.

Add the following secrets:

### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `HETZNER_HOST` | IP address or domain of your VPS | `192.168.1.100` or `dutchworkbook.com` |
| `HETZNER_USER` | SSH username for deployment | `dutchapp` |
| `HETZNER_SSH_KEY` | Private SSH key for authentication | See key generation below |
| `HETZNER_PORT` | SSH port (optional, defaults to 22) | `22` or `2222` |

### Generating SSH Key for Deployment

On your local machine or VPS:

```bash
# Generate a new SSH key pair (do this on your local machine)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/dutchworkbook_deploy

# This creates:
#   ~/.ssh/dutchworkbook_deploy (private key)
#   ~/.ssh/dutchworkbook_deploy.pub (public key)
```

**Add the PUBLIC key to VPS:**

```bash
# On VPS, add to authorized_keys of the app user
cat ~/.ssh/dutchworkbook_deploy.pub | ssh dutchapp@your-vps-ip "cat >> ~/.ssh/authorized_keys"
```

**Add the PRIVATE key to GitHub Secrets:**

```bash
# Display the private key
cat ~/.ssh/dutchworkbook_deploy
```

Copy the entire output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`) and paste it as the value for `HETZNER_SSH_KEY` secret.

## Step 2: VPS Initial Setup

SSH into your VPS and run these commands:

### 2.1 Create Application User (if not exists)

```bash
sudo useradd -m -s /bin/bash dutchapp
sudo mkdir -p /opt/dutchworkbook
sudo chown -R dutchapp:dutchapp /opt/dutchworkbook
```

### 2.2 Clone Repository

```bash
sudo -u dutchapp bash -c "cd /opt && git clone https://github.com/yourusername/dutch-workbook.git"
```

### 2.3 Install Dependencies

```bash
sudo -u dutchapp bash << 'EOF'
cd /opt/dutchworkbook

# Install UV if not present
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

export PATH="$HOME/.cargo/bin:$PATH"
uv sync
EOF
```

### 2.4 Create Production Settings

Create `/opt/dutchworkbook/nederlandse_workbook/production_settings.py`:

```python
import os
from .settings import *

# SECURITY SETTINGS
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com', 'localhost', '127.0.0.1']
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# DATABASE
# The committed production_settings.py selects the engine via the DB_ENGINE env
# var (defaults to SQLite). For PostgreSQL, set the DB_* env vars instead of
# editing this file, e.g.:
#   DB_ENGINE=django.db.backends.postgresql
#   DB_NAME=dutchworkbook
#   DB_USER=dutchapp
#   DB_PASSWORD=your-secure-password
#   DB_HOST=localhost
#   DB_PORT=5432
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', 'dutchworkbook'),
        'USER': os.getenv('DB_USER', 'dutchapp'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# STATIC FILES
STATIC_ROOT = '/opt/dutchworkbook/staticfiles'
STATIC_URL = '/static/'

# MEDIA FILES
MEDIA_ROOT = '/opt/dutchworkbook/media'
MEDIA_URL = '/media/'

# SECURITY
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 2.5 Setup Systemd Service

Create `/etc/systemd/system/dutchworkbook.service`:

```ini
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
ExecStart=/opt/dutchworkbook/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 nederlandse_workbook.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5
Timeout=30

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dutchworkbook
sudo systemctl start dutchworkbook
```

#### 2.5.1 Generation Job Processor (systemd Timer)

AI word generation is queued as `WordGenerationJob` rows and processed by a
management command (`process_generation_jobs`), not a background thread. This
makes generation durable across deploys/restarts. A systemd timer runs the
processor every 15 seconds. The unit files live in the repo root
(`dutchworkbook-jobs.service` / `dutchworkbook-jobs.timer`) and are installed
by `setup-vps.sh`:

```bash
sudo cp /opt/dutchworkbook/dutchworkbook-jobs.service /etc/systemd/system/
sudo cp /opt/dutchworkbook/dutchworkbook-jobs.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dutchworkbook-jobs.timer
```

Verify it is active and check recent runs:

```bash
sudo systemctl status dutchworkbook-jobs.timer
sudo systemctl list-timers dutchworkbook-jobs.timer
# Logs of individual runs:
journalctl -u dutchworkbook-jobs.service -n 50 --no-pager
```

### 2.6 Configure Nginx

Create `/etc/nginx/sites-available/dutchworkbook`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration (configure with certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Static files
    location /static/ {
        alias /opt/dutchworkbook/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/dutchworkbook/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

Enable the site:

```bash
sudo ln -sf /etc/nginx/sites-available/dutchworkbook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2.7 Setup SSL with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Step 3: How the CI/CD Pipeline Works

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) does the following:

### On Pull Requests and Pushes to main/develop:
1. **Test Job** (Python 3.12):
   - Sets up Python and installs dependencies with `uv`
   - Runs `ruff check` (linting)
   - Runs `ruff format --check` (formatting)
   - Runs `makemigrations --check --dry-run` (checks for missing migrations)
   - Runs the Django test suite

2. **Deploy Job** (only on push to main):
   - Pushes the code directly to the VPS via `git push` over SSH into `/opt/dutchworkbook`
   - Restores repo ownership to the app user
   - Syncs dependencies with `uv sync`
   - Runs migrations
   - Compiles translation messages (`compilemessages`)
   - Collects static files
   - Restarts the gunicorn service

The deploy user (from the `HETZNER_USER` secret) needs SSH access to the VPS and permission to push into `/opt/dutchworkbook` and restart the `dutchworkbook` systemd service. The `dutchapp` user does not need to run `sudo` — the workflow only switches to `dutchapp` for the app workload.

## Step 4: Manual Deployment

If you need to deploy manually without CI/CD:

```bash
# SSH into your VPS
ssh dutchapp@your-vps-ip

# Run the deployment script
cd /opt/dutchworkbook
./deploy-hetzner.sh
```

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status dutchworkbook
sudo journalctl -u dutchworkbook -f
```

### Check Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Test Django Manually
```bash
sudo -u dutchapp bash -c "cd /opt/dutchworkbook && export PATH=\"\$HOME/.cargo/bin:\$PATH\" && uv run python manage.py check --settings nederlandse_workbook.production_settings"
```

### Rollback Deployment
```bash
# List backups
ls -la /opt/dutchworkbook/backups/

# Restore from backup
cd /opt
sudo rm -rf dutchworkbook
sudo tar -xzf /opt/dutchworkbook/backups/pre-deploy-YYYYMMDD-HHMMSS.tar.gz
sudo chown -R dutchapp:dutchapp /opt/dutchworkbook
sudo systemctl restart dutchworkbook
```

## Security Recommendations

1. **Firewall**: Configure UFW or firewalld
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   ```

2. **Fail2ban**: Install to prevent brute-force attacks
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

3. **Automatic Updates**: Set up unattended-upgrades
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

4. **Database Backups**: Set up automated backups. The app currently runs on SQLite
   (default), so back up the database file. If you migrate to PostgreSQL, switch this
   cron to `pg_dump` instead:
   ```bash
   # Add to crontab
   # SQLite (current):
   0 2 * * * cp /opt/dutchworkbook/db.sqlite3 /opt/dutchworkbook/backups/db_$(date +\%Y\%m\%d).sqlite3 && find /opt/dutchworkbook/backups -name 'db_*.sqlite3' -mtime +30 -delete

   # PostgreSQL (after migrating):
   # 0 2 * * * pg_dump -h localhost -U dutchapp dutchworkbook > /opt/dutchworkbook/backups/db_$(date +\%Y\%m\%d).sql
   ```

## Monitoring

Consider setting up monitoring with:
- **Prometheus + Grafana** for metrics
- **Sentry** for error tracking
- **Uptime Robot** for uptime monitoring

---

For more information, check the main `README.md` or open an issue on GitHub.
