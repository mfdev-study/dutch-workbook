"""
Tests for words app - models, views, and services.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from words.models import Example, Flashcard, Word, WordList

User = get_user_model()


class WordModelTest(TestCase):
    """Test Word model."""

    def setUp(self):
        self.word = Word.objects.create(
            dutch="hond", translation="dog", source="EN", part_of_speech="noun"
        )

    def test_word_creation(self):
        """Test word is created correctly."""
        self.assertEqual(self.word.dutch, "hond")
        self.assertEqual(self.word.translation, "dog")
        self.assertEqual(self.word.source, "EN")

    def test_word_str(self):
        """Test word string representation."""
        self.assertEqual(str(self.word), "hond - dog")

    def test_unique_constraint(self):
        """Test unique constraint on dutch+translation+source."""
        with self.assertRaises(IntegrityError):
            Word.objects.create(dutch="hond", translation="dog", source="EN")


class WordListViewTest(TestCase):
    """Test WordList model and functionality."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.word1 = Word.objects.create(dutch="kat", translation="cat", source="EN")
        self.word2 = Word.objects.create(dutch="boom", translation="tree", source="EN")

    def test_wordlist_creation(self):
        """Test creating a word list."""
        wordlist = WordList.objects.create(user=self.user, name="My List", list_type="FAV")
        wordlist.words.add(self.word1, self.word2)
        self.assertEqual(wordlist.words.count(), 2)


class FlashcardModelTest(TestCase):
    """Test Flashcard model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.word = Word.objects.create(dutch="huis", translation="house", source="EN")

    def test_flashcard_creation(self):
        """Test flashcard creation."""
        from django.utils import timezone

        flashcard = Flashcard.objects.create(
            user=self.user, word=self.word, box=1, next_review=timezone.now()
        )
        self.assertEqual(flashcard.box, 1)
        self.assertEqual(flashcard.user, self.user)

    def test_unique_flashcard(self):
        """Test unique constraint on user+word."""
        Flashcard.objects.create(user=self.user, word=self.word, box=1)
        with self.assertRaises(IntegrityError):
            Flashcard.objects.create(user=self.user, word=self.word, box=2)


class WordViewsTest(TestCase):
    """Test words views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.word = Word.objects.create(dutch="boek", translation="book", source="EN")

    def test_dashboard_view(self):
        """Test dashboard loads correctly."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_browse_words_view(self):
        """Test browse words page."""
        response = self.client.get(reverse("browse"))
        self.assertEqual(response.status_code, 200)

    def test_browse_words_search(self):
        """Test search functionality."""
        response = self.client.get(reverse("browse"), {"q": "boek"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "boek")

    def test_word_detail_view(self):
        """Test word detail page."""
        response = self.client.get(reverse("word_detail", args=[self.word.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "boek")

    def test_add_word_view_get(self):
        """Test add word page loads."""
        response = self.client.get(reverse("add_word"))
        self.assertEqual(response.status_code, 200)

    def test_add_word_view_post(self):
        """Test adding a new word."""
        data = {
            "dutch": "auto",
            "translation": "car",
            "source": "EN",
        }
        response = self.client.post(reverse("add_word"), data)
        self.assertEqual(response.status_code, 302)  # Redirect to word detail
        self.assertTrue(Word.objects.filter(dutch="auto").exists())

    def test_add_flashcard(self):
        """Test adding a flashcard for a word."""
        response = self.client.get(reverse("add_flashcard", args=[self.word.id]))
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(Flashcard.objects.filter(user=self.user, word=self.word).exists())


class ExampleModelTest(TestCase):
    """Test Example model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.word = Word.objects.create(dutch="lopen", translation="walk", source="EN")

    def test_example_creation(self):
        """Test creating an example."""
        example = Example.objects.create(
            word=self.word,
            text="Ik loop naar huis.",
            translation="I walk to the house.",
            created_by=self.user,
        )
        self.assertEqual(example.word, self.word)
        self.assertEqual(example.created_by, self.user)
