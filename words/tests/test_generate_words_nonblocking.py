"""Tests for non-blocking word generation view."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from words.models import Word


class GenerateWordsNonBlockingTest(TestCase):
    """Test cases for non-blocking word generation."""

    def setUp(self):
        self.client = self.client  # Django test client
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")
        # Clear cache before each test
        cache.clear()

    def test_get_request_shows_form(self):
        """GET request should show the generation form."""
        with patch("words.views.settings") as mock_settings:
            mock_settings.OPENCODE_ENABLED = True

            response = self.client.get(reverse("generate_words"))
            self.assertEqual(response.status_code, 200)
            self.assertIn("levels", response.context)
            self.assertIn("sources", response.context)

    def test_ajax_polling_pending_when_no_cache(self):
        """AJAX polling should return 'pending' when no result in cache."""
        response = self.client.get(reverse("generate_words") + "?check=true")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "pending")

    @patch("words.views.WordGenerationService")
    def test_ajax_polling_done_after_background_complete(self, mock_service_class):
        """AJAX polling should return 'done' when background task completes."""
        # Create a test word
        word = Word.objects.create(
            dutch="testword",
            translation="testword",
            source="EN",
        )

        # Simulate background task completed - store result in cache.
        result_key = f"gen_result_{self.user.id}"
        cache.set(
            result_key,
            {
                "word_ids": [word.id],
                "words_skipped": 0,
                "model_used": "test-model",
            },
            timeout=300,
        )

        response = self.client.get(reverse("generate_words") + "?check=true")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "done")
        self.assertEqual(len(data["word_ids"]), 1)
        self.assertEqual(data["word_ids"][0], word.id)

    @patch("words.views.WordGenerationService")
    def test_ajax_polling_error_when_generation_fails(self, mock_service_class):
        """AJAX polling should return 'error' when generation fails."""
        # Simulate background task failed
        result_key = f"gen_result_{self.user.id}"
        cache.set(
            result_key,
            {"error": "AI response parse error"},
            timeout=300,
        )

        response = self.client.get(reverse("generate_words") + "?check=true")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")
        self.assertIn("parse error", data["message"].lower())

    def test_post_request_without_opencode_enabled(self):
        """POST request should show error when OpenCode is not enabled."""
        with patch("words.views.settings") as mock_settings:
            mock_settings.OPENCODE_ENABLED = False

            response = self.client.post(
                reverse("generate_words"),
                {"count": "3", "level": "A2", "source": "EN"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("error", response.context)
            self.assertIn("not enabled", response.context["error"].lower())

    def test_completed_result_display_after_reload(self):
        """After background completes, page reload should show results."""
        # Create test words
        word1 = Word.objects.create(
            dutch="huis", translation="house", source="EN", part_of_speech="noun"
        )
        word2 = Word.objects.create(
            dutch="boom", translation="tree", source="EN", part_of_speech="noun"
        )

        # Simulate background task completed.
        result_key = f"gen_result_{self.user.id}"
        cache.set(
            result_key,
            {
                "word_ids": [word1.id, word2.id],
                "words_skipped": 1,
                "model_used": "test-model",
            },
            timeout=300,
        )

        with patch("words.views.settings") as mock_settings:
            mock_settings.OPENCODE_ENABLED = True

            response = self.client.get(reverse("generate_words"))
            self.assertEqual(response.status_code, 200)

            # Should have words_created in context
            self.assertIn("words_created", response.context)
            self.assertEqual(len(response.context["words_created"]), 2)
            self.assertEqual(response.context["words_skipped"], 1)
            self.assertEqual(response.context["model_used"], "test-model")

            # Cache should be cleared after displaying
            self.assertIsNone(cache.get(result_key))

    def test_cache_key_is_user_specific(self):
        """Cache key should be specific to each user."""
        # Create another user
        get_user_model().objects.create_user(username="testuser2", password="testpass123")

        # Set result for user1
        result_key1 = f"gen_result_{self.user.id}"
        cache.set(result_key1, {"word_ids": [1, 2]}, timeout=300)

        # User2 should not see user1's result
        self.client.logout()
        self.client.login(username="testuser2", password="testpass123")

        response = self.client.get(reverse("generate_words") + "?check=true")
        data = json.loads(response.content)
        self.assertEqual(data["status"], "pending")

    def test_settings_has_cache_configured(self):
        """Settings should have CACHES configured."""
        from django.conf import settings

        self.assertIn("CACHES", dir(settings))
        self.assertIn("default", settings.CACHES)
        self.assertEqual(
            settings.CACHES["default"]["BACKEND"], "django.core.cache.backends.locmem.LocMemCache"
        )

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("generate_words"))
        self.assertEqual(response.status_code, 302)

    def test_generating_state_in_template(self):
        """Template should show generating spinner when in progress."""
        with patch("words.views.settings") as mock_settings:
            mock_settings.OPENCODE_ENABLED = True

            # Simulate generation in progress (cache has data but no word_ids yet)
            result_key = f"gen_result_{self.user.id}"
            cache.set(result_key, {"status": "generating"}, timeout=300)

            response = self.client.get(reverse("generate_words"))
            self.assertEqual(response.status_code, 200)

            # Template should show generating state
            content = response.content.decode().lower()
            self.assertIn("generating", content)
            # Check for spinner (animate-spin class)
            self.assertIn("animate-spin", content)
