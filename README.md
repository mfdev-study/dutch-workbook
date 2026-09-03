# Dutch Workbook

A Django-based web application for learning Dutch vocabulary using flashcards, quizzes, and spaced repetition.

## Features

- **Vocabulary Management**: Add, browse, and organize Dutch words with translations
- **Flashcards**: Spaced repetition system for effective learning
- **Quizzes**: Test your knowledge with interactive quizzes
- **Progress Tracking**: Monitor your learning progress and maintain streaks
- **AI Word Generation**: Generate new vocabulary words using AI
- **Categories**: Organize words into custom categories
- **Multi-language Support**: Available in English, Dutch, Russian, and Ukrainian
- **Favorites**: Mark words for quick access

## Technology Stack

- **Backend**: Django 6.x (Python)
- **Database**: SQLite (default in dev and prod); PostgreSQL supported via `DB_ENGINE`
- **Frontend**: Tailwind CSS, Alpine.js
- **Internationalization**: Django i18n with gettext
- **Deployment**: Hetzner VPS with Gunicorn + Nginx
- **CI/CD**: GitHub Actions

## Prerequisites

- Python 3.12+ 
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Git
- gettext (for translations)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/dutch-workbook.git
cd dutch-workbook
```

### 2. Set Up Development Environment

```bash
make setup
```

Or manually:

```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate --settings=nederlandse_workbook.settings

# Create superuser (optional)
uv run python manage.py createsuperuser --settings=nederlandse_workbook.settings
```

### 3. Run the Development Server

```bash
make runserver
```

Or:

```bash
uv run python manage.py runserver --settings=nederlandse_workbook.settings
```

Visit `http://127.0.0.1:8000` in your browser.

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_PASSWORD=your-db-password
```

### Production Settings

For production deployment, create `nederlandse_workbook/production_settings.py`. The
database engine is selected by the `DB_ENGINE` env var: it defaults to SQLite, but set
`DB_ENGINE=django.db.backends.postgresql` (with the `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, `DB_PORT` env vars) to run PostgreSQL:

```python
import os
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dutchworkbook',
        'USER': 'dutchapp',
        'PASSWORD': 'your-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ... additional production settings
```

## Internationalization

The app supports multiple languages:

- English (default)
- Dutch (Nederlands)
- Russian (Русский)
- Ukrainian (Українська)

### Adding Translations

1. Edit translation files in `locale/<language>/LC_MESSAGES/django.po`
2. Compile translations:
   ```bash
   make translate
   ```

### Switching Languages

Users can switch languages using the language switcher in the navigation menu.

## Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific app tests
uv run python manage.py test words --settings=nederlandse_workbook.settings
```

## Code Quality

```bash
# Lint code
make lint

# Format code
make format
```

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

## Deployment

### Automated Deployment (CI/CD)

The project uses GitHub Actions for CI/CD. On push to `main` branch:

1. Tests and linting run automatically
2. If successful, the code deploys to Hetzner VPS

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup instructions.

### Manual Deployment

```bash
make deploy
```

Or on the server:

```bash
cd /opt/dutchworkbook
./deploy-hetzner.sh
```

## Project Structure

```
dutch-workbook/
├── accounts/           # User authentication app
├── words/             # Vocabulary and flashcard management
├── quiz/              # Quiz functionality
├── progress/          # Progress tracking
├── nederlandse_workbook/  # Project configuration
├── templates/         # HTML templates
├── locale/            # Translation files
├── static/            # Static files
├── media/             # User-uploaded files
├── .github/           # GitHub Actions workflows
├── deploy-hetzner.sh  # Deployment script
├── Makefile           # Development commands
└── README.md          # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Django framework
- Tailwind CSS
- Alpine.js
- Dutch language learning resources

## Support

For support, please open an issue on GitHub or contact the maintainers.

---

**Happy Learning! 🇳🇱**
