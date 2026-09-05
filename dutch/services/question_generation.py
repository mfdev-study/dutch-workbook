"""
AI-powered Dutch de/het article question generation service.
"""

import json
import logging
import re
from dataclasses import dataclass

from dutch.models import DutchArticleQuestion
from nederlandse_workbook.utils.opencode import OpenCodeClient

logger = logging.getLogger(__name__)

SOURCE_LANGUAGE_MAP = {
    "EN": "English",
    "RU": "Russian",
    "UK": "Ukrainian",
}

VALID_ARTICLES = ("de", "het")

VALID_CATEGORIES = (
    "plural",
    "person",
    "diminutive",
    "ing",
    "heid",
    "memorize",
)

VALID_LEVELS = ("A1", "A2")


@dataclass
class ArticleQuestionGenerationRequest:
    count: int = 5
    level: str = "A1"
    category: str | None = None
    source: str = "EN"
    model: str | None = None


@dataclass
class GeneratedArticleQuestion:
    word: str
    translation: str
    correct_article: str
    explanation: str
    category: str
    level: str


class ArticleQuestionGenerationService:
    """Service for AI-powered de/het quiz question generation."""

    def __init__(self, client: OpenCodeClient | None = None):
        self.client = client or OpenCodeClient()

    def generate_questions(
        self, request: ArticleQuestionGenerationRequest
    ) -> tuple[str | None, list[GeneratedArticleQuestion]]:
        """Generate de/het questions using AI."""
        prompt = self._build_prompt(request)
        used_model, response = self.client.chat(prompt, model=request.model)

        if not response:
            return used_model, []

        questions_data = self._parse_response(response)
        return used_model, [self._to_generated_question(q, request.level) for q in questions_data]

    def save_questions(
        self,
        questions: list[GeneratedArticleQuestion],
    ) -> tuple[list[DutchArticleQuestion], list[DutchArticleQuestion]]:
        """Save generated questions to database.

        Questions that fail validation (bad article, category, empty word) are
        skipped, as are duplicates already present in the database.
        """
        created_questions = []
        skipped_questions = []

        for question_data in questions:
            word = question_data.word.strip()
            article = question_data.correct_article.strip()
            category = question_data.category.strip()

            if (
                not word
                or article not in VALID_ARTICLES
                or category not in VALID_CATEGORIES
                or not question_data.explanation.strip()
            ):
                skipped_questions.append(question_data)
                continue

            question, created = DutchArticleQuestion.objects.get_or_create(
                word=word,
                defaults={
                    "translation": question_data.translation.strip(),
                    "correct_article": article,
                    "explanation": question_data.explanation.strip(),
                    "category": category,
                    "level": question_data.level,
                },
            )

            if created:
                created_questions.append(question)
            else:
                skipped_questions.append(question)

        return created_questions, skipped_questions

    def _build_prompt(self, request: ArticleQuestionGenerationRequest) -> str:
        """Build the prompt for AI question generation."""
        source_name = SOURCE_LANGUAGE_MAP.get(request.source, "English")
        category_str = (
            f"All questions must belong to the category '{request.category}'.\n"
            if request.category
            else ""
        )

        return f"""Generate {request.count} Dutch de/het article quiz questions at CEFR level {request.level}.
Translate each translation field to {source_name}.
{category_str}
Return ONLY a JSON array with this exact structure:
[
  {{
    "word": "kinderen",
    "translation": "children",
    "correct_article": "de",
    "explanation": "Kinderen is a plural noun, so it uses de.",
    "category": "plural"
  }}
]

Rules for choosing the correct article:
- Plural nouns -> de
- People/professions -> usually de
- Diminutives ending in -je -> het
- Nouns ending in -ing -> de
- Nouns ending in -heid -> de
- Other words -> choose between de and het (category 'memorize')
Must return exactly {request.count} questions now. Categories allowed: {", ".join(VALID_CATEGORIES)}."""

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

    def _to_generated_question(self, data: dict, level: str) -> GeneratedArticleQuestion:
        """Convert dict to GeneratedArticleQuestion dataclass."""
        return GeneratedArticleQuestion(
            word=data.get("word", ""),
            translation=data.get("translation", ""),
            correct_article=data.get("correct_article", ""),
            explanation=data.get("explanation", ""),
            category=data.get("category", ""),
            level=level if level in VALID_LEVELS else "A1",
        )


def generate_de_het_questions(
    count: int = 5,
    level: str = "A1",
    category: str | None = None,
    source: str = "EN",
) -> tuple[str | None, list[GeneratedArticleQuestion]]:
    """Convenience function for de/het question generation."""
    service = ArticleQuestionGenerationService()

    request = ArticleQuestionGenerationRequest(
        count=count,
        level=level,
        category=category,
        source=source,
    )

    return service.generate_questions(request)
