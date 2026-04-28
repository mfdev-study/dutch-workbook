"""
Tests for quiz app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from words.models import Word

User = get_user_model()


class QuizViewsTest(TestCase):
    """Test quiz views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.word1 = Word.objects.create(dutch="appel", translation="apple", source="EN")
        self.word2 = Word.objects.create(dutch="banaan", translation="banana", source="EN")

    def test_quiz_home_view(self):
        """Test quiz home page loads."""
        response = self.client.get(reverse("quiz_home"))
        self.assertEqual(response.status_code, 200)

    def test_start_quiz(self):
        """Test starting a new quiz."""
        data = {
            "quiz_type": "multiple_choice",
            "word_count": 5,
        }
        response = self.client.post(reverse("start_quiz", args=["multiple_choice"]), data)
        # Should redirect to quiz question page
        self.assertIn(response.status_code, [200, 302])
