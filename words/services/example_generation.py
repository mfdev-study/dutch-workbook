"""
AI-powered example sentence generation service.
"""

import json
import logging
import re
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from nederlandse_workbook.utils.opencode import OpenCodeClient
from words.models import Example

logger = logging.getLogger(__name__)

SYSTEM_USERNAME = "ai"


@dataclass
class GeneratedExample:
    word: str = ""
    text: str = ""
    translation: str = ""


class ExampleGenerationService:
    """Service for AI-powered Dutch example sentence generation."""

    def __init__(self, client: OpenCodeClient | None = None):
        self.client = client or OpenCodeClient()

    def generate_examples(
        self, words: list, language: str, model: str | None = None
    ) -> tuple[str | None, list[GeneratedExample]]:
        """Generate example sentences for words using AI."""
        prompt = self._build_prompt(words, language)
        used_model, response = self.client.chat(prompt, model=model)

        if not response:
            return used_model, []

        examples_data = self._parse_response(response)
        return used_model, [self._to_generated_example(e) for e in examples_data]

    def save_examples(
        self,
        word,
        examples: list[GeneratedExample],
        created_by,
    ) -> tuple[list[Example], list[Example]]:
        """Save generated examples to database, skipping duplicates."""
        created_examples = []
        skipped_examples = []

        for example in examples:
            text = example.text.strip()
            if not text:
                skipped_examples.append(example)
                continue

            example_obj, created = Example.objects.get_or_create(
                word=word,
                text=text,
                defaults={
                    "translation": example.translation.strip(),
                    "created_by": created_by,
                },
            )

            if created:
                created_examples.append(example_obj)
            else:
                skipped_examples.append(example_obj)

        return created_examples, skipped_examples

    def _build_prompt(self, words: list, language: str) -> str:
        """Build the prompt for AI example generation."""
        word_lines = "\n".join(f"{i + 1}. {w.dutch}" for i, w in enumerate(words))

        return f"""Generate one simple Dutch example sentence for each word below.
Translate each example sentence to {language}.

Words:
{word_lines}

Return ONLY a JSON array with this exact structure:
[
  {{
    "word": "het huis",
    "text": "Dit is een mooi huis.",
    "translation": "Це гарний будинок."
  }}
]

Requirements:
- Exactly one example per word, in the same order as the Words list
- "word" must match the word exactly
- Sentences must be simple, natural, and grammatically correct
- "translation" is the example sentence translated to {language}

Generate exactly {len(words)} examples now."""

    def _parse_response(self, response: str) -> list[dict]:
        """Parse JSON response from AI."""
        response_clean = self._clean_response(response)

        json_match = re.search(r"\[.*\]", response_clean, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(response_clean)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        return []

    def _clean_response(self, response: str) -> str:
        """Strip ANSI codes, tool log lines, and markdown fences from AI output."""
        from nederlandse_workbook.utils.opencode import _strip_ansi

        cleaned = _strip_ansi(response)
        # Remove tool log lines (e.g. "> build · big-pickle, → Read file.json")
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith((">", "→"))
        )
        # Strip markdown code block markers
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        # Strip any leading non-JSON content before the first [
        cleaned = re.sub(r"^[^[]*", "", cleaned.strip())
        return cleaned

    def _to_generated_example(self, data: dict) -> GeneratedExample:
        """Convert dict to GeneratedExample dataclass."""
        return GeneratedExample(
            word=data.get("word", ""),
            text=data.get("text", ""),
            translation=data.get("translation", ""),
        )


def get_or_create_ai_user():
    """Get or create the system 'ai' user used to attribute generated examples."""
    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username=SYSTEM_USERNAME,
        defaults={"is_staff": False, "is_superuser": False},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user
