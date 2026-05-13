"""
AI-powered word generation service.
"""

import json
import logging
import re
from dataclasses import dataclass

from nederlandse_workbook.utils.opencode import OpenCodeClient
from words.models import Word

logger = logging.getLogger(__name__)


SOURCE_LANGUAGE_MAP = {
    "EN": "English",
    "RU": "Russian",
    "UK": "Ukrainian",
}

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1"]


@dataclass
class WordGenerationRequest:
    count: int = 5
    level: str = "A2"
    theme: str | None = None
    source: str = "EN"
    model: str | None = None


@dataclass
class GeneratedWord:
    dutch: str
    translation: str
    part_of_speech: str
    context: str
    example: str
    example_translation: str = ""


class WordGenerationService:
    """Service for AI-powered Dutch vocabulary word generation."""

    def __init__(self, client: OpenCodeClient | None = None):
        self.client = client or OpenCodeClient()

    def generate_words(
        self, request: WordGenerationRequest
    ) -> tuple[str | None, list[GeneratedWord]]:
        """Generate Dutch words using AI."""
        prompt = self._build_prompt(request)
        used_model, response = self.client.chat(prompt, model=request.model)

        if not response:
            return used_model, []

        words_data = self._parse_response(response)
        return used_model, [self._to_generated_word(w) for w in words_data]

    def save_words(
        self,
        words: list[GeneratedWord],
        source: str,
    ) -> tuple[list[Word], list[Word]]:
        """Save generated words to database."""
        created_words = []
        skipped_words = []

        for word_data in words:
            word, created = Word.objects.get_or_create(
                dutch=word_data.dutch.strip(),
                translation=word_data.translation.strip(),
                source=source,
                defaults={
                    "part_of_speech": word_data.part_of_speech,
                    "context": word_data.context,
                    "example": word_data.example,
                    "example_translation": word_data.example_translation,
                },
            )

            if created:
                created_words.append(word)
            else:
                skipped_words.append(word)

        return created_words, skipped_words

    def _build_prompt(self, request: WordGenerationRequest) -> str:
        """Build the prompt for AI word generation."""
        source_name = SOURCE_LANGUAGE_MAP.get(request.source, "English")
        theme_str = f"Theme: {request.theme}\n" if request.theme else ""

        return f"""Generate {request.count} Dutch vocabulary words at CEFR level {request.level}.
{theme_str}Translate to {source_name}.

Return ONLY a JSON array with this exact structure:
[
  {{
    "dutch": "het woord",
    "translation": "the word",
    "part_of_speech": "noun",
    "context": "daily life",
    "example": "Dit is een voorbeeld zin.",
    "example_translation": "Це приклад речення."
  }}
]

Requirements:
- Dutch words must be accurate and natural
- Include article (de/het) for nouns
- Part of speech: noun, verb, adjective, adverb, etc.
- Context: brief topic tags
- Example: simple Dutch sentence using the word
- Example translation: translate the example to {source_name}

Generate exactly {request.count} words now."""

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
        """Remove code blocks from response."""
        cleaned = re.sub(r"^```json\s*", "", response.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned

    def _to_generated_word(self, data: dict) -> GeneratedWord:
        """Convert dict to GeneratedWord dataclass."""
        return GeneratedWord(
            dutch=data.get("dutch", ""),
            translation=data.get("translation", ""),
            part_of_speech=data.get("part_of_speech", ""),
            context=data.get("context", ""),
            example=data.get("example", ""),
            example_translation=data.get("example_translation", ""),
        )


def generate_words(
    count: int = 5,
    level: str = "A2",
    theme: str | None = None,
    source: str = "EN",
) -> tuple[str | None, list[GeneratedWord]]:
    """Convenience function for word generation."""
    service = WordGenerationService()

    request = WordGenerationRequest(
        count=count,
        level=level,
        theme=theme,
        source=source,
    )

    return service.generate_words(request)
