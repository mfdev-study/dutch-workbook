"""
Tests for the generate_word_examples management command and example generation service.
"""

from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from words.models import Example, Word
from words.services.example_generation import (
    SYSTEM_USERNAME,
    ExampleGenerationService,
    GeneratedExample,
    get_or_create_ai_user,
)


class AiUserTests(TestCase):
    """Tests for the get_or_create_ai_user helper."""

    def test_creates_user(self):
        self.assertFalse(get_user_model().objects.filter(username=SYSTEM_USERNAME).exists())
        user = get_or_create_ai_user()
        self.assertEqual(user.username, SYSTEM_USERNAME)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_idempotent(self):
        first = get_or_create_ai_user()
        second = get_or_create_ai_user()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(get_user_model().objects.filter(username=SYSTEM_USERNAME).count(), 1)

    def test_has_unusable_password(self):
        user = get_or_create_ai_user()
        self.assertFalse(user.has_usable_password())


class ExampleServiceTests(TestCase):
    """Tests for ExampleGenerationService."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="testuser", password="pass123")
        self.word = Word.objects.create(dutch="de auto", translation="car", source="EN")
        self.service = ExampleGenerationService(client=Mock())

    def test_save_examples_creates_rows(self):
        examples = [
            GeneratedExample(word="de auto", text="Ik rij een auto.", translation="I drive a car.")
        ]
        created, skipped = self.service.save_examples(self.word, examples, self.user)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].text, "Ik rij een auto.")
        self.assertEqual(created[0].translation, "I drive a car.")
        self.assertEqual(created[0].created_by, self.user)
        self.assertEqual(Example.objects.count(), 1)

    def test_save_examples_skips_duplicate_text(self):
        Example.objects.create(word=self.word, text="Ik rij een auto.", created_by=self.user)
        examples = [
            GeneratedExample(word="de auto", text="Ik rij een auto.", translation="duplicate")
        ]
        created, skipped = self.service.save_examples(self.word, examples, self.user)
        self.assertEqual(len(created), 0)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(Example.objects.count(), 1)

    def test_save_examples_skips_empty_text(self):
        examples = [GeneratedExample(word="de auto", text="", translation="empty")]
        created, skipped = self.service.save_examples(self.word, examples, self.user)
        self.assertEqual(len(created), 0)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(Example.objects.count(), 0)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_generate_examples_calls_client(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "de auto", "text": "Ik rij een auto.", "translation": "I drive a car."}]',
        )
        mock_client_class.return_value = mock_client

        service = ExampleGenerationService()
        used_model, examples = service.generate_examples([self.word], language="English")

        self.assertEqual(used_model, "test-model")
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].text, "Ik rij een auto.")
        self.assertEqual(examples[0].translation, "I drive a car.")

    def test_generate_examples_empty_response(self):
        mock_client = Mock()
        mock_client.chat.return_value = (None, "")
        service = ExampleGenerationService(client=mock_client)

        used_model, examples = service.generate_examples([self.word], language="English")
        self.assertIsNone(used_model)
        self.assertEqual(examples, [])


@override_settings(OPENCODE_ENABLED=False)
class GenerateWordExamplesDisabledTests(TestCase):
    """Tests when OpenCode is disabled."""

    def test_command_fails(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("generate_word_examples", stdout=StringIO())
        self.assertIn("OpenCode is not enabled", str(ctx.exception))


@override_settings(OPENCODE_ENABLED=True)
class GenerateWordExamplesCommandTests(TestCase):
    """Tests for the generate_word_examples management command."""

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.user = get_user_model().objects.create_user(username="testuser", password="pass123")
        self.word = Word.objects.create(dutch="het huis", translation="house", source="UK")

    @patch("words.services.example_generation.OpenCodeClient")
    def test_generates_and_saves(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "het huis", "text": "Dit is een groot huis.", "translation": "Це великий будинок."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Example.objects.count(), 1)
        example = Example.objects.first()
        self.assertEqual(example.word, self.word)
        self.assertEqual(example.text, "Dit is een groot huis.")
        self.assertEqual(example.translation, "Це великий будинок.")
        self.assertEqual(example.created_by.username, SYSTEM_USERNAME)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_dry_run_saves_nothing(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "het huis", "text": "Dit is een huis.", "translation": "Це будинок."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", dry_run=True, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Example.objects.count(), 0)
        output = self.stdout.getvalue()
        self.assertIn("DRY RUN", output)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_invalid_json_returns_zero(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", "This is not valid JSON")
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Example.objects.count(), 0)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_no_words_to_process(self, mock_client_class):
        Example.objects.create(word=self.word, text="already has", created_by=self.user)
        call_command("generate_word_examples", stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Example.objects.count(), 1)
        mock_client_class.return_value.chat.assert_not_called()

    @patch("words.services.example_generation.OpenCodeClient")
    def test_prompt_contains_words_and_language(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", "[]")
        mock_client_class.return_value = mock_client

        call_command(
            "generate_word_examples",
            language="UK",
            stdout=self.stdout,
            stderr=self.stderr,
        )

        prompt = mock_client.chat.call_args[0][0]
        self.assertIn("het huis", prompt)
        self.assertIn("Ukrainian", prompt)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_created_by_username(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "het huis", "text": "Zin.", "translation": "Sentence."}]',
        )
        mock_client_class.return_value = mock_client

        call_command(
            "generate_word_examples",
            created_by="testuser",
            stdout=self.stdout,
            stderr=self.stderr,
        )

        example = Example.objects.first()
        self.assertEqual(example.created_by, self.user)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_created_by_nonexistent_user_fails(self, mock_client_class):
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "generate_word_examples",
                created_by="ghost",
                stdout=self.stdout,
                stderr=self.stderr,
            )
        self.assertIn("ghost", str(ctx.exception))

    @patch("words.services.example_generation.OpenCodeClient")
    def test_match_examples_by_word_field(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "het huis", "text": "Forbeeld.", "translation": "Example."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", stdout=self.stdout, stderr=self.stderr)

        example = Example.objects.first()
        self.assertEqual(example.word, self.word)
        self.assertEqual(example.text, "Forbeeld.")

    @patch("words.services.example_generation.OpenCodeClient")
    def test_positional_fallback_when_word_field_missing(self, mock_client_class):
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"text": "Test zin.", "translation": "Test sentence."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", stdout=self.stdout, stderr=self.stderr)

        example = Example.objects.first()
        self.assertEqual(example.word, self.word)

    @patch("words.services.example_generation.OpenCodeClient")
    def test_limit_flag(self, mock_client_class):
        Word.objects.create(dutch="de stoel", translation="chair", source="EN")
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"word": "de stoel", "text": "Zin.", "translation": "Sentence."}]',
        )
        mock_client_class.return_value = mock_client

        call_command("generate_word_examples", limit=1, stdout=self.stdout, stderr=self.stderr)

        self.assertEqual(Example.objects.count(), 1)
        self.assertEqual(Example.objects.first().word.dutch, "de stoel")
