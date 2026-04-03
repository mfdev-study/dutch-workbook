"""
Tests for the generate_words_view web interface.
"""

from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from words.models import Category, Word
from words.services.word_generation import GeneratedWord


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
        self.assertEqual(response.status_code, 302)

    def test_view_get_request(self):
        """Test GET request to view."""
        with override_settings(OPENCODE_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "words/generate_words.html")
        self.assertIn("levels", response.context)
        self.assertIn("sources", response.context)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_post_generates_words(self, mock_service_class):
        """Test POST request generates words."""

        mock_word = Word(id=1, dutch="de hond", translation="the dog", source="EN")
        mock_word.save = Mock()

        mock_service = Mock()
        mock_service.generate_words.return_value = (
            "test-model",
            [
                GeneratedWord(
                    dutch="de hond",
                    translation="the dog",
                    part_of_speech="noun",
                    context="animals",
                    example="De hond loopt in het park.",
                )
            ],
        )
        mock_service.save_words.return_value = ([mock_word], [])
        mock_service_class.return_value = mock_service

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

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_post_with_category(self, mock_service_class):
        """Test POST request with category assignment."""

        category, _ = Category.objects.get_or_create(name="Animals")
        mock_word = Word(id=1, dutch="de kat", translation="the cat", source="EN")
        mock_word.save = Mock()

        mock_service = Mock()
        mock_service.generate_words.return_value = (
            "test-model",
            [
                GeneratedWord(
                    dutch="de kat",
                    translation="the cat",
                    part_of_speech="noun",
                    context="animals",
                    example="De kat slaapt.",
                )
            ],
        )
        mock_service.save_words.return_value = ([mock_word], [])
        mock_service_class.return_value = mock_service

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

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_handles_invalid_json(self, mock_service_class):
        """Test view handles invalid JSON response."""
        mock_service = Mock()
        mock_service.generate_words.return_value = ("test-model", [])
        mock_service_class.return_value = mock_service

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

    @override_settings(OPENCODE_ENABLED=False)
    def test_view_shows_error_when_disabled(self):
        """Test view shows error when OpenCode is disabled."""
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

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_skips_duplicates(self, mock_service_class):
        """Test that view skips duplicate words."""

        Word.objects.create(dutch="de auto", translation="the car", source="EN")
        mock_word = Word(id=1, dutch="de auto", translation="the car", source="EN")

        mock_service = Mock()
        mock_service.generate_words.return_value = (
            "test-model",
            [
                GeneratedWord(
                    dutch="de auto",
                    translation="the car",
                    part_of_speech="noun",
                    context="transport",
                    example="Ik rijdt een auto.",
                )
            ],
        )
        mock_service.save_words.return_value = ([], [mock_word])
        mock_service_class.return_value = mock_service

        response = self.client.post(
            reverse("generate_words"),
            {
                "count": "1",
                "level": "A2",
                "source": "EN",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("words_skipped", response.context)
        self.assertEqual(len(response.context["words_skipped"]), 1)

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_shows_model_used(self, mock_service_class):
        """Test that view shows which model was used."""

        mock_word = Word(id=1, dutch="de fiets", translation="the bicycle", source="EN")
        mock_word.save = Mock()

        mock_service = Mock()
        mock_service.generate_words.return_value = (
            "opencode/minimax-m2.5-free",
            [
                GeneratedWord(
                    dutch="de fiets",
                    translation="the bicycle",
                    part_of_speech="noun",
                    context="transport",
                    example="Ik fies naar school.",
                )
            ],
        )
        mock_service.save_words.return_value = ([mock_word], [])
        mock_service_class.return_value = mock_service

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
        self.assertEqual(response.context["model_used"], "opencode/minimax-m2.5-free")

    @override_settings(OPENCODE_ENABLED=True)
    @patch("words.views.WordGenerationService")
    def test_view_handles_api_error(self, mock_service_class):
        """Test view handles API errors gracefully."""
        mock_service = Mock()
        mock_service.generate_words.side_effect = Exception("API Error")
        mock_service_class.return_value = mock_service

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

        Category.objects.all().delete()
        Category.objects.create(name="Test Category 1")
        Category.objects.create(name="Test Category 2")

        with override_settings(OPENCODE_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("categories", response.context)
        self.assertEqual(len(response.context["categories"]), 2)

    def test_view_context_includes_levels(self):
        """Test that view context includes CEFR levels."""
        with override_settings(OPENCODE_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("levels", response.context)
        self.assertEqual(response.context["levels"], ["A1", "A2", "B1", "B2", "C1"])

    def test_view_context_includes_sources(self):
        """Test that view context includes translation sources."""
        with override_settings(OPENCODE_ENABLED=True):
            response = self.client.get(reverse("generate_words"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("sources", response.context)
        self.assertIn(("EN", "English"), response.context["sources"])
        self.assertIn(("RU", "Russian"), response.context["sources"])
        self.assertIn(("UK", "Ukrainian"), response.context["sources"])
