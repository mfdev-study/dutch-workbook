"""
Tests for the generate_words_view web interface.
"""

from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from words.models import Category, Word


class GenerateWordsViewTests(TestCase):
    """Tests for the generate_words_view."""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("generate_words"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_view_get_request(self):
        """Test GET request to view."""
        with override_settings(OPENROUTER_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "words/generate_words.html")
        self.assertIn("levels", response.context)
        self.assertIn("sources", response.context)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_post_generates_words(self, mock_client_class):
        """Test POST request generates words."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de hond", "translation": "the dog", "part_of_speech": "noun"}]',
        )
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
                "theme": "animals",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("words_created", response.context)
        self.assertEqual(len(response.context["words_created"]), 1)

        # Verify word was created
        self.assertEqual(Word.objects.count(), 1)
        word = Word.objects.first()
        self.assertEqual(word.dutch, "de hond")

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_post_with_category(self, mock_client_class):
        """Test POST request with category assignment."""
        category = Category.objects.create(name="Animals")

        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de kat", "translation": "the cat"}]',
        )
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
                "category": str(category.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        word = Word.objects.first()
        self.assertIsNotNone(word)
        self.assertTrue(word.categorized.filter(category=category).exists())

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_handles_invalid_json(self, mock_client_class):
        """Test view handles invalid JSON response."""
        mock_client = Mock()
        mock_client.chat.return_value = ("test-model", "Invalid response")
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)
        self.assertIn("raw_response", response.context)

    @override_settings(OPENROUTER_ENABLED=False)
    def test_view_shows_error_when_disabled(self):
        """Test view shows error when OpenRouter is disabled."""
        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)
        self.assertIn("not enabled", response.context["error"])

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_skips_duplicates(self, mock_client_class):
        """Test that view skips duplicate words."""
        # Create existing word
        Word.objects.create(dutch="de auto", translation="the car", source="EN")

        mock_client = Mock()
        mock_client.chat.return_value = (
            "test-model",
            '[{"dutch": "de auto", "translation": "the car"}]',
        )
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        # Should show skipped words
        self.assertIn("words_skipped", response.context)
        self.assertEqual(len(response.context["words_skipped"]), 1)

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_shows_model_used(self, mock_client_class):
        """Test that view shows which model was used."""
        mock_client = Mock()
        mock_client.chat.return_value = (
            "anthropic/claude-3.5-sonnet",
            '[{"dutch": "de fiets", "translation": "the bicycle"}]',
        )
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("model_used", response.context)
        self.assertEqual(response.context["model_used"], "anthropic/claude-3.5-sonnet")

    @override_settings(OPENROUTER_ENABLED=True, OPENROUTER_API_KEY="test-key")
    @patch("words.views.OpenRouterClient")
    def test_view_handles_api_error(self, mock_client_class):
        """Test view handles API errors gracefully."""
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)
        self.assertIn("API Error", response.context["error"])

    def test_view_context_includes_categories(self):
        """Test that view context includes categories."""
        Category.objects.create(name="Category 1")
        Category.objects.create(name="Category 2")

        with override_settings(OPENROUTER_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("categories", response.context)
        self.assertEqual(len(response.context["categories"]), 2)

    def test_view_context_includes_levels(self):
        """Test that view context includes CEFR levels."""
        with override_settings(OPENROUTER_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("levels", response.context)
        self.assertEqual(response.context["levels"], ["A1", "A2", "B1", "B2", "C1"])

    def test_view_context_includes_sources(self):
        """Test that view context includes translation sources."""
        with override_settings(OPENROUTER_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("sources", response.context)
        self.assertIn(("EN", "English"), response.context["sources"])
        self.assertIn(("RU", "Russian"), response.context["sources"])
        self.assertIn(("UK", "Ukrainian"), response.context["sources"])
