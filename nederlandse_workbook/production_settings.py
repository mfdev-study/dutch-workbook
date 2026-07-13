import os

from .settings import *  # noqa: F401, F403

# SECURITY SETTINGS
DEBUG = False
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# SSL/HTTPS Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "https://workbook.mfdev.nl").split(",")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# DATABASE (SQLite)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DB_PATH", os.path.join(BASE_DIR, "db.sqlite3")),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}

# STATIC FILES
STATIC_ROOT = os.getenv("STATIC_ROOT", os.path.join(BASE_DIR, "staticfiles"))
STATIC_URL = "/static/"

# MEDIA FILES
MEDIA_ROOT = os.getenv("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))
MEDIA_URL = "/media/"

# LOGGING
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "django.log"),
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "words": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# EMAIL (optional - for notifications)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@dutchworkbook.com")

# Performance settings
CONN_MAX_AGE = 60
