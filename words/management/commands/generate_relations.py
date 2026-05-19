"""
Management command to generate semantic relations between Dutch words using AI.
"""

import logging

from django.core.management.base import BaseCommand

from words.services.relation_generation import RelationGenerationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate semantic relations between Dutch words using AI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of words per batch (default: 50)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many words would be processed without saving",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        from words.models import Word

        total_words = Word.objects.count()

        if total_words == 0:
            self.stdout.write(self.style.WARNING("No words found in the database."))
            return

        self.stdout.write(f"Found {total_words} words in the database.")
        self.stdout.write(
            f"Will process in batches of {batch_size} "
            f"({(total_words + batch_size - 1) // batch_size} batches total)"
        )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        self.stdout.write("Generating relations... (this may take a while)")

        try:
            service = RelationGenerationService()
            total = service.generate_relations(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(f"Successfully created {total} relations!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error generating relations: {e}"))
            raise
