"""
Tests for progress app.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DailyActivity, UserProgress, update_streak

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


class UpdateStreakTest(TestCase):
    """Test the update_streak helper."""

    def setUp(self):
        self.user = User.objects.create_user(username="streakuser", password="testpass123")
        self.today = timezone.now().date()

    def _create_activity(self, day_offset, words_reviewed=1):
        DailyActivity.objects.create(
            user=self.user,
            date=self.today - timedelta(days=day_offset),
            words_reviewed=words_reviewed,
        )

    def test_no_activity_clears_streak(self):
        progress, _ = UserProgress.objects.get_or_create(user=self.user)
        progress.current_streak = 5
        progress.longest_streak = 5
        progress.save()

        update_streak(self.user)
        progress.refresh_from_db()
        self.assertEqual(progress.current_streak, 0)
        self.assertIsNone(progress.last_activity)

    def test_single_day_streak(self):
        self._create_activity(0)
        update_streak(self.user)
        progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(progress.current_streak, 1)
        self.assertEqual(progress.longest_streak, 1)
        self.assertEqual(progress.last_activity, self.today)

    def test_consecutive_days(self):
        self._create_activity(0)
        self._create_activity(1)
        self._create_activity(2)
        update_streak(self.user)
        progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(progress.current_streak, 3)
        self.assertEqual(progress.longest_streak, 3)

    def test_gap_breaks_streak(self):
        self._create_activity(0)
        self._create_activity(1)
        self._create_activity(3)  # gap on day 2
        update_streak(self.user)
        progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(progress.current_streak, 2)
        self.assertEqual(progress.longest_streak, 2)

    def test_zero_activity_excluded(self):
        self._create_activity(0, words_reviewed=0)
        update_streak(self.user)
        progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(progress.current_streak, 0)

