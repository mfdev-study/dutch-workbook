"""
Management command to generate Dutch words using OpenCode AI.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from words.services.word_generation import (
    GeneratedWord,
    WordGenerationRequest,
    WordGenerationService,
)


class Command(BaseCommand):
    help = "Generate Dutch words using AI (OpenCode)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of words to generate (default: 5)",
        )
        parser.add_argument(
            "--level",
            type=str,
            choices=["A1", "A2", "B1", "B2", "C1"],
            default="A2",
            help="CEFR language level (default: A2)",
        )
        parser.add_argument(
            "--theme",
            type=str,
            help="Theme/topic for words (e.g., 'food', 'travel', 'work')",
        )
        parser.add_argument(
            "--source",
            type=str,
            choices=["EN", "RU", "UK"],
            default="EN",
            help="Translation language (EN=English, RU=Russian, UK=Ukrainian)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show generated words without saving to database",
        )
        parser.add_argument(
            "--model",
            type=str,
            help="OpenCode model to use",
        )

    def handle(self, *args, **options):
        if not settings.OPENCODE_ENABLED:
            raise CommandError(
                "OpenCode is not enabled. Please ensure opencode-auto is installed and in PATH."
            )

        service = WordGenerationService()

        source = options["source"]
        request = WordGenerationRequest(
            count=options["count"],
            level=options["level"],
            theme=options.get("theme"),
            source=source,
            model=options.get("model"),
        )

        self.stdout.write(f"Generating {request.count} Dutch words (Level: {request.level})")
        if request.theme:
            self.stdout.write(f"Theme: {request.theme}")
        self.stdout.write(f"Translation: {source}")
        self.stdout.write("")

        try:
            used_model, generated_words = service.generate_words(request)
            self.stdout.write(f"Model used: {used_model}")
            self.stdout.write("")
        except Exception as e:
            raise CommandError(f"Failed to generate words: {e}") from e

        if not generated_words:
            self.stdout.write(self.style.WARNING("No words could be parsed from AI response"))
            return

        for word in generated_words:
            self._display_word(word)

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: {len(generated_words)} words generated but not saved")
            )
        else:
            created, skipped = service.save_words(generated_words, source)
            self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created)} words"))
            if skipped:
                self.stdout.write(f"Skipped {len(skipped)} duplicate words")

    def _display_word(self, word: GeneratedWord) -> None:
        """Display word information."""
        self.stdout.write(f"Dutch: {word.dutch}")
        self.stdout.write(f"  Translation: {word.translation}")
        if word.part_of_speech:
            self.stdout.write(f"  Part of speech: {word.part_of_speech}")
        if word.context:
            self.stdout.write(f"  Context: {word.context}")
        if word.example:
            self.stdout.write(f"  Example: {word.example}")
        self.stdout.write("")
