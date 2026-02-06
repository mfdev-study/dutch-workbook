import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a timestamped backup of the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Directory to save backup (default: backups/)",
            default="backups",
        )
        parser.add_argument(
            "--keep",
            type=int,
            help="Number of backups to keep (default: 10)",
            default=10,
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        keep_count = options["keep"]

        # Create output directory
        output_dir.mkdir(exist_ok=True)

        # Get database path
        db_path = Path(settings.DATABASES["default"]["NAME"])

        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Database not found at {db_path}"))
            return

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_backup_{timestamp}.sqlite3"
        backup_path = output_dir / backup_filename

        try:
            # Copy the database file
            shutil.copy2(db_path, backup_path)

            # Clean up old backups
            backups = sorted(output_dir.glob("db_backup_*.sqlite3"), reverse=True)
            if len(backups) > keep_count:
                for old_backup in backups[keep_count:]:
                    old_backup.unlink()
                    self.stdout.write(f"Removed old backup: {old_backup.name}")

            backup_size = backup_path.stat().st_size / 1024  # KB
            self.stdout.write(
                self.style.SUCCESS(
                    f"Database backup created: {backup_filename} ({backup_size:.1f} KB)"
                )
            )
            self.stdout.write(f"Location: {backup_path}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Backup failed: {e}"))
