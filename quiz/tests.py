"""
Tests for quiz app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from progress.models import UserProgress
from quiz.models import QuizSession
from words.models import Flashcard, Word

User = get_user_model()


class QuizViewsTest(TestCase):
    """Test quiz views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.word1 = Word.objects.create(dutch="appel", translation="apple", source="EN")
        self.word2 = Word.objects.create(dutch="banaan", translation="banana", source="EN")

    def _add_flashcards(self):
        for word in (self.word1, self.word2):
            Flashcard.objects.create(user=self.user, word=word)

    def test_quiz_home_view(self):
        """Test quiz home page loads."""
        response = self.client.get(reverse("quiz_home"))
        self.assertEqual(response.status_code, 200)

    def test_start_quiz(self):
        """Test starting a new quiz with a valid quiz type."""
        self._add_flashcards()
        response = self.client.get(reverse("start_quiz", args=["MC"]))
        self.assertEqual(response.status_code, 302)
        session = QuizSession.objects.get(user=self.user)
        self.assertEqual(session.quiz_type, "MC")
        self.assertEqual(session.total, 2)

    def test_start_quiz_invalid_type(self):
        """Test that an invalid quiz type redirects without creating a session."""
        self._add_flashcards()
        response = self.client.get(reverse("start_quiz", args=["XX"]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(QuizSession.objects.filter(user=self.user).exists())

    def test_submit_correct_answer(self):
        """Test submitting the correct answer via server-side question tracking."""
        self._add_flashcards()
        self.client.get(reverse("start_quiz", args=["MC"]))
        word_ids = self.client.session["quiz_word_ids"]
        current_word = Word.objects.get(id=word_ids[0])

        response = self.client.post(reverse("submit_answer"), {"answer_id": current_word.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["quiz_score"], 1)

    def test_submit_wrong_answer(self):
        """Test submitting a wrong answer."""
        self._add_flashcards()
        self.client.get(reverse("start_quiz", args=["MC"]))
        word_ids = self.client.session["quiz_word_ids"]
        wrong_id = next(wid for wid in word_ids if wid != word_ids[0])

        self.client.post(reverse("submit_answer"), {"answer_id": wrong_id})
        self.assertEqual(self.client.session["quiz_score"], 0)

    def test_cheating_by_spoofed_word_id_is_impossible(self):
        """Test that posting a matching word_id/answer_id pair cannot cheat.

        The old implementation trusted the client-supplied word_id, so posting
        identical IDs always counted as correct. The server must derive the
        current question from the session instead.
        """
        self._add_flashcards()
        self.client.get(reverse("start_quiz", args=["MC"]))
        word_ids = self.client.session["quiz_word_ids"]
        not_current = self.word1.id if word_ids[0] != self.word1.id else self.word2.id

        response = self.client.post(
            reverse("submit_answer"),
            {"word_id": not_current, "answer_id": not_current},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["quiz_score"], 0)

    def test_submit_answer_requires_post(self):
        """Test that GET requests are rejected and don't record answers."""
        self._add_flashcards()
        self.client.get(reverse("start_quiz", args=["MC"]))
        word_ids = self.client.session["quiz_word_ids"]

        response = self.client.get(reverse("submit_answer"), {"answer_id": word_ids[0]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["quiz_current"], 0)
        self.assertEqual(self.client.session["quiz_score"], 0)

    def test_average_score_stored_as_percentage(self):
        """Test that progress average score is a percentage, not a raw score."""
        self._add_flashcards()
        self.client.get(reverse("start_quiz", args=["MC"]))
        word_ids = self.client.session["quiz_word_ids"]

        for word_id in word_ids:
            self.client.post(reverse("submit_answer"), {"answer_id": word_id})

        self.client.get(reverse("quiz_results"))

        progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(progress.average_score, 100.0)
