"""
Management command to generate Dutch words using OpenRouter AI.
"""

import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from nederlandse_workbook.utils.openrouter import OpenRouterClient
from words.models import Category, Word


class Command(BaseCommand):
    help = "Generate Dutch words using AI (OpenRouter)"

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
            "--category",
            type=str,
            help="Category name to assign generated words to",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show generated words without saving to database",
        )
        parser.add_argument(
            "--model",
            type=str,
            help="OpenRouter model to use (overrides OPENROUTER_MODEL setting)",
        )

    def handle(self, *args, **options):
        if not settings.OPENROUTER_ENABLED:
            raise CommandError(
                "OpenRouter is not enabled. Please set OPENROUTER_API_KEY environment variable."
            )

        count = options["count"]
        level = options["level"]
        theme = options.get("theme")
        source = options["source"]
        category_name = options.get("category")
        dry_run = options["dry_run"]
        model = options.get("model")

        # Map source to full language name
        source_names = {"EN": "English", "RU": "Russian", "UK": "Ukrainian"}
        source_name = source_names.get(source, "English")

        self.stdout.write(f"Generating {count} Dutch words (Level: {level})")
        if theme:
            self.stdout.write(f"Theme: {theme}")
        self.stdout.write(f"Translation: {source_name}")
        if category_name:
            self.stdout.write(f"Category: {category_name}")
        self.stdout.write("")

        # Get category if specified
        category = None
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name)
            self.stdout.write(f"Using category: {category.name}")

        # Build prompt
        prompt = self.build_prompt(count, level, theme, source_name)

        # Generate words
        try:
            client = OpenRouterClient()
            used_model, response = client.chat(prompt, model=model)
            self.stdout.write(f"Model used: {used_model}")
            self.stdout.write("")
        except Exception as e:
            raise CommandError(f"Failed to generate words: {e}") from e

        # Parse response
        words_data = self.parse_response(response)

        if not words_data:
            self.stdout.write(self.style.WARNING("No words could be parsed from AI response"))
            return

        # Display and save words
        words_created = 0
        words_skipped = 0

        for word_data in words_data:
            self.display_word(word_data)

            if not dry_run:
                word, created = self.save_word(word_data, source)
                if created:
                    words_created += 1
                    if category:
                        from words.models import CategorizedWord

                        CategorizedWord.objects.create(word=word, category=category)
                        self.stdout.write(f"  Added to category: {category.name}")
                else:
                    words_skipped += 1
                    self.stdout.write(self.style.WARNING("  Word already exists"))

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: {len(words_data)} words generated but not saved")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {words_created} words"))
            if words_skipped > 0:
                self.stdout.write(f"Skipped {words_skipped} duplicate words")

    def build_prompt(self, count: int, level: str, theme: str | None, source_name: str) -> str:
        """Build the prompt for AI word generation."""
        theme_str = f"Theme: {theme}\n" if theme else ""

        prompt = f"""Generate {count} Dutch vocabulary words at CEFR level {level}.
{theme_str}Translate to {source_name}.

Return ONLY a JSON array with this exact structure:
[
  {{
    "dutch": "het woord",
    "translation": "the word",
    "part_of_speech": "noun",
    "context": "daily life",
    "example": "Dit is een voorbeeld zin."
  }}
]

Requirements:
- Dutch words must be accurate and natural
- Include article (de/het) for nouns
- Part of speech: noun, verb, adjective, adverb, etc.
- Context: brief topic tags
- Example: simple Dutch sentence using the word

Generate exactly {count} words now."""

        return prompt

    def parse_response(self, response: str) -> list[dict]:
        """Parse JSON response from AI."""
        # Try to find JSON array in response
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Try to parse entire response as JSON
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        return []

    def display_word(self, word_data: dict) -> None:
        """Display word information."""
        dutch = word_data.get("dutch", "Unknown")
        translation = word_data.get("translation", "")
        pos = word_data.get("part_of_speech", "")
        context = word_data.get("context", "")
        example = word_data.get("example", "")

        self.stdout.write(f"Dutch: {dutch}")
        self.stdout.write(f"  Translation: {translation}")
        if pos:
            self.stdout.write(f"  Part of speech: {pos}")
        if context:
            self.stdout.write(f"  Context: {context}")
        if example:
            self.stdout.write(f"  Example: {example}")
        self.stdout.write("")

    def save_word(self, word_data: dict, source: str) -> tuple[Word, bool]:
        """Save word to database. Returns (word, created)."""
        dutch = word_data.get("dutch", "").strip()
        translation = word_data.get("translation", "").strip()
        pos = word_data.get("part_of_speech", "")
        context = word_data.get("context", "")
        example = word_data.get("example", "")

        word, created = Word.objects.get_or_create(
            dutch=dutch,
            translation=translation,
            source=source,
            defaults={
                "part_of_speech": pos,
                "context": context,
                "example": example,
            },
        )

        return word, created
