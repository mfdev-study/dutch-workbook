"""
Tests for progress app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ProgressViewsTest(TestCase):
    """Test progress views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_progress_view(self):
        """Test progress page loads."""
        response = self.client.get(reverse("progress"))
        self.assertEqual(response.status_code, 200)

    def test_streak_view(self):
        """Test streak page loads."""
        response = self.client.get(reverse("streak"))
        self.assertEqual(response.status_code, 200)
