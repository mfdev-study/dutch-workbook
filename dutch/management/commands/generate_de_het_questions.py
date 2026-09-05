"""
Management command to generate Dutch de/het quiz questions using OpenCode AI.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dutch.services.question_generation import (
    VALID_CATEGORIES,
    VALID_LEVELS,
    ArticleQuestionGenerationRequest,
    ArticleQuestionGenerationService,
    GeneratedArticleQuestion,
)


class Command(BaseCommand):
    help = "Generate Dutch de/het article quiz questions using AI (OpenCode)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of questions to generate (default: 5)",
        )
        parser.add_argument(
            "--level",
            type=str,
            choices=list(VALID_LEVELS),
            default="A1",
            help="CEFR level (default: A1)",
        )
        parser.add_argument(
            "--category",
            type=str,
            choices=list(VALID_CATEGORIES),
            help="Force a single category",
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
            help="Show generated questions without saving to database",
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

        service = ArticleQuestionGenerationService()

        request = ArticleQuestionGenerationRequest(
            count=options["count"],
            level=options["level"],
            category=options.get("category"),
            source=options["source"],
            model=options.get("model"),
        )

        self.stdout.write(f"Generating {request.count} de/het questions (Level: {request.level})")
        if request.category:
            self.stdout.write(f"Category: {request.category}")
        self.stdout.write(f"Translation: {request.source}")
        self.stdout.write("")

        try:
            used_model, generated = service.generate_questions(request)
            self.stdout.write(f"Model used: {used_model}")
            self.stdout.write("")
        except Exception as e:
            raise CommandError(f"Failed to generate questions: {e}") from e

        if not generated:
            self.stdout.write(self.style.WARNING("No questions could be parsed from AI response"))
            return

        for question in generated:
            self._display_question(question)

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: {len(generated)} questions generated but not saved")
            )
        else:
            created, skipped = service.save_questions(generated)
            self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created)} questions"))
            if skipped:
                self.stdout.write(f"Skipped {len(skipped)} invalid or duplicate questions")

    def _display_question(self, question: GeneratedArticleQuestion) -> None:
        """Display question information."""
        self.stdout.write(f"Word: {question.correct_article} {question.word}")
        if question.translation:
            self.stdout.write(f"  Translation: {question.translation}")
        self.stdout.write(f"  Category: {question.category}")
        self.stdout.write(f"  Explanation: {question.explanation}")
        self.stdout.write("")
