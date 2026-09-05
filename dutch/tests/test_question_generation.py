"""
Tests for the generate_de_het_questions management command.
"""

import json
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from dutch.models import DutchArticleQuestion


class GenerateDeHetQuestionsCommandTests(TestCase):
    """Tests for the generate_de_het_questions management command."""

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.valid_question = {
            "word": "meisjes",
            "translation": "girls",
            "correct_article": "de",
            "explanation": "Meisjes is a plural noun, so it uses de.",
            "category": "plural",
        }

    @override_settings(OPENCODE_ENABLED=False)
    def test_command_fails_when_opencode_disabled(self):
        """Test that command fails when OpenCode is not enabled."""
        with self.assertRaises(CommandError) as context:
            call_command("generate_de_het_questions", stdout=self.stdout, stderr=self.stderr)

        self.assertIn("OpenCode is not enabled", str(context.exception))

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_generates_questions_successfully(self, mock_client_class):
        """Test successful question generation."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(DutchArticleQuestion.objects.count(), before + 1)
        question = DutchArticleQuestion.objects.order_by("-id").first()
        self.assertEqual(question.word, "meisjes")
        self.assertEqual(question.correct_article, "de")
        self.assertEqual(question.category, "plural")
        self.assertEqual(question.level, "A1")

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_dry_run(self, mock_client_class):
        """Test that dry-run doesn't save questions."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command(
            "generate_de_het_questions",
            count=1,
            dry_run=True,
            stdout=self.stdout,
            stderr=self.stderr,
        )

        self.assertEqual(DutchArticleQuestion.objects.count(), before)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_skips_duplicates(self, mock_client_class):
        """Test that duplicate questions are skipped."""
        DutchArticleQuestion.objects.create(
            word="meisjes",
            translation="girls",
            correct_article="de",
            explanation="Plural uses de.",
            category="plural",
        )

        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(DutchArticleQuestion.objects.count(), before)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_handles_invalid_json(self, mock_client_class):
        """Test handling of invalid JSON response."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", "This is not valid JSON")
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(DutchArticleQuestion.objects.count(), before)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_skips_invalid_correct_article(self, mock_client_class):
        """Test that a question with an invalid article is not saved."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "huis", "translation": "house", "correct_article": "den", "explanation": "Memorize this one.", "category": "memorize"}]',
        )
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(DutchArticleQuestion.objects.count(), before)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_skips_invalid_category(self, mock_client_class):
        """Test that a question with an invalid category is not saved."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "huis", "translation": "house", "correct_article": "het", "explanation": "Memorize this one.", "category": "bogus"}]',
        )
        mock_client_class.return_value = mock_client

        before = DutchArticleQuestion.objects.count()
        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(DutchArticleQuestion.objects.count(), before)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_prompt_contains_level(self, mock_client_class):
        """Test that the prompt contains the requested CEFR level."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        call_command("generate_de_het_questions", count=1, stdout=self.stdout, stderr=self.stderr)

        call_args = mock_client.chat.call_args
        self.assertIn("A1", call_args[0][0])

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_prompt_contains_category(self, mock_client_class):
        """Test that the prompt includes a forced category."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        call_command(
            "generate_de_het_questions",
            count=1,
            category="diminutive",
            stdout=self.stdout,
            stderr=self.stderr,
        )

        call_args = mock_client.chat.call_args
        self.assertIn("diminutive", call_args[0][0])

    @override_settings(OPENCODE_ENABLED=True)
    @patch("dutch.services.question_generation.OpenCodeClient")
    def test_command_prompt_contains_source(self, mock_client_class):
        """Test that the prompt includes the translation source language."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", f"[{json.dumps(self.valid_question)}]")
        mock_client_class.return_value = mock_client

        call_command(
            "generate_de_het_questions",
            count=1,
            source="UK",
            stdout=self.stdout,
            stderr=self.stderr,
        )

        call_args = mock_client.chat.call_args
        self.assertIn("Ukrainian", call_args[0][0])
