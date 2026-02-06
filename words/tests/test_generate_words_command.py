"""
Tests for the generate_words management command.
"""

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from words.models import Category, Word


class GenerateWordsCommandTests(TestCase):
    """Tests for the generate_words management command."""

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    @override_settings(OPENROUTER_ENABLED=False)
    def test_command_fails_when_openrouter_disabled(self):
        """Test that command fails when OpenRouter is not enabled."""
        with self.assertRaises(CommandError) as context:
            call_command("generate_words", stdout=self.stdout, stderr=self.stderr)

        self.assertIn("OpenRouter is not enabled", str(context.exception))

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_generates_words_successfully(self, mock_client_class):
        """Test successful word generation."""
        # Mock the client response
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "het huis", "translation": "the house", "part_of_speech": "noun", "context": "daily life", "example": "Ik woon in een huis."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_words", count=1, stdout=self.stdout, stderr=self.stderr)

        # Check that a word was created
        self.assertEqual(Word.objects.count(), 1)
        word = Word.objects.first()
        self.assertEqual(word.dutch, "het huis")
        self.assertEqual(word.translation, "the house")

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_with_category(self, mock_client_class):
        """Test word generation with category assignment."""
        category = Category.objects.create(name="Test Category")

        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "het boek", "translation": "the book", "part_of_speech": "noun"}]',
        )
        mock_client_class.return_value = mock_client

        call_command(
            "generate_words",
            count=1,
            category="Test Category",
            stdout=self.stdout,
            stderr=self.stderr,
        )

        word = Word.objects.first()
        self.assertIsNotNone(word)
        self.assertTrue(word.categorized.filter(category=category).exists())

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_dry_run(self, mock_client_class):
        """Test that dry-run doesn't save words."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de auto", "translation": "the car"}]',
        )
        mock_client_class.return_value = mock_client

        call_command(
            "generate_words", count=1, dry_run=True, stdout=self.stdout, stderr=self.stderr
        )

        # No words should be created
        self.assertEqual(Word.objects.count(), 0)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_skips_duplicates(self, mock_client_class):
        """Test that duplicate words are skipped."""
        # Create existing word
        Word.objects.create(dutch="de tafel", translation="the table", source="EN")

        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de tafel", "translation": "the table"}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_words", count=1, stdout=self.stdout, stderr=self.stderr)

        # Should still only have 1 word
        self.assertEqual(Word.objects.count(), 1)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_parses_json_array(self, mock_client_class):
        """Test parsing of JSON array from AI response."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            'Here are some words:\n\n[\n  {"dutch": "de hond", "translation": "the dog"},\n  {"dutch": "de kat", "translation": "the cat"}\n]\n\nHope this helps!',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_words", count=2, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Word.objects.count(), 2)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_handles_invalid_json(self, mock_client_class):
        """Test handling of invalid JSON response."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", "This is not valid JSON")
        mock_client_class.return_value = mock_client

        call_command("generate_words", count=1, stdout=self.stdout, stderr=self.stderr)

        # No words should be created
        self.assertEqual(Word.objects.count(), 0)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_with_theme(self, mock_client_class):
        """Test word generation with theme."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de appel", "translation": "the apple"}]',
        )
        mock_client_class.return_value = mock_client

        call_command(
            "generate_words", count=1, theme="food", stdout=self.stdout, stderr=self.stderr
        )

        # Verify the prompt included the theme
        call_args = mock_client.chat.call_args
        self.assertIn("food", call_args[0][0])

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.management.commands.generate_words.OpenRouterClient")
    def test_command_with_different_sources(self, mock_client_class):
        """Test word generation with different translation sources."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de auto", "translation": "the car"}]',
        )
        mock_client_class.return_value = mock_client

        # Test Russian source
        call_command("generate_words", count=1, source="RU", stdout=self.stdout, stderr=self.stderr)

        word = Word.objects.first()
        self.assertEqual(word.source, "RU")

        # Verify Russian was mentioned in prompt
        call_args = mock_client.chat.call_args
        self.assertIn("Russian", call_args[0][0])
