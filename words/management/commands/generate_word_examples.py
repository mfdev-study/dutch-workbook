"""
Management command to generate example sentences using OpenCode AI.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from words.models import Word
from words.services.example_generation import (
    ExampleGenerationService,
    get_or_create_ai_user,
)
from words.services.word_generation import SOURCE_LANGUAGE_MAP


class Command(BaseCommand):
    help = "Generate example sentences for existing words using AI (OpenCode)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of words to process (0 = all words missing examples)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            dest="batch_size",
            help="Words per AI request (default: 10)",
        )
        parser.add_argument(
            "--language",
            type=str,
            choices=["EN", "RU", "UK"],
            help="Translation language for examples (default: word's source language)",
        )
        parser.add_argument(
            "--created-by",
            type=str,
            help="Username to attribute generated examples to (default: system 'ai' user)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show generated examples without saving to database",
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

        service = ExampleGenerationService()
        language_override = options.get("language")
        created_by = self._resolve_created_by(options.get("created_by"))

        words_qs = Word.objects.filter(examples__isnull=True).order_by("dutch")
        if options["limit"]:
            words_qs = words_qs[: options["limit"]]
        words = list(words_qs)

        if not words:
            self.stdout.write("No words missing examples.")
            return

        total_created = 0
        total_skipped = 0
        batch_size = options["batch_size"]

        for group_key, group_words in self._group_by(
            words, self._resolve_source_key(language_override)
        ):
            language = SOURCE_LANGUAGE_MAP.get(group_key, "English")
            self.stdout.write(
                f"Generating examples for {len(group_words)} words "
                f"(Language: {language}, Batch: {batch_size})"
            )
            self.stdout.write("")

            for batch in self._chunks(group_words, batch_size):
                try:
                    used_model, generated = service.generate_examples(
                        batch, language=language, model=options.get("model")
                    )
                except Exception as e:
                    raise CommandError(f"Failed to generate examples: {e}") from e

                self.stdout.write(f"Model used: {used_model}")
                if not generated:
                    self.stdout.write(
                        self.style.WARNING("No examples could be parsed from AI response")
                    )
                    continue

                matched = self._match_examples(batch, generated)

                if options["dry_run"]:
                    self._display_batch(batch, matched)
                    continue

                for word, word_examples in matched.items():
                    created, skipped = service.save_examples(word, word_examples, created_by)
                    total_created += len(created)
                    total_skipped += len(skipped)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: examples generated but not saved"))
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"Successfully created {total_created} examples"))
            if total_skipped:
                self.stdout.write(f"Skipped {total_skipped} invalid or duplicate examples")

    def _resolve_created_by(self, username: str | None):
        if username:
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(username=username).first()
            if user is None:
                raise CommandError(f"User '{username}' does not exist.")
            return user
        user = get_or_create_ai_user()
        if user.password == "":
            self.stdout.write(
                self.style.NOTICE(f"Created system user '{user.username}' for attribution")
            )
        return user

    @staticmethod
    def _group_by(items, key_func):
        groups: dict = {}
        for item in items:
            groups.setdefault(key_func(item), []).append(item)
        return groups.items()

    @staticmethod
    def _resolve_source_key(language_override: str | None):
        if language_override:

            def _by_override(word):
                return language_override

            return _by_override

        def _by_source(word):
            return word.source

        return _by_source

    def _chunks(self, items, size):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _match_examples(self, batch, generated):
        """Match generated examples to words by the word field, falling back to position."""
        by_word = {}
        for example in generated:
            if example.word:
                by_word.setdefault(example.word.strip().lower(), []).append(example)

        used = set()
        matched = {}
        for word in batch:
            key = word.dutch.strip().lower()
            by_key = by_word.get(key) or []
            examples = [e for e in by_key if id(e) not in used]
            if not examples:
                for candidate in generated:
                    if id(candidate) not in used:
                        examples = [candidate]
                        break
            for example in examples:
                used.add(id(example))
            matched[word] = [e for e in examples if e.text.strip()]
        return matched

    def _display_batch(self, batch, matched):
        for word, examples in matched.items():
            self.stdout.write(f"Dutch: {word.dutch}")
            for example in examples:
                if example.text:
                    self.stdout.write(f"  Example: {example.text}")
                    if example.translation:
                        self.stdout.write(f"  Translation: {example.translation}")
            self.stdout.write("")
