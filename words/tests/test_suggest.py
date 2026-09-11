"""Tests for words app - word suggestions (smart search)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from words.models import Word

User = get_user_model()


class WordSuggestTest(TestCase):
    """Test the HTMX word suggestion endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="suggester", password="testpass123")
        self.client.login(username="suggester", password="testpass123")

    def _get(self, params=None, htmx=True):
        kwargs = {}
        if htmx:
            kwargs["HTTP_HX_REQUEST"] = "true"
        return self.client.get(reverse("word_suggest"), params or {}, **kwargs)

    # -- accessibility / guards -------------------------------------------------

    def test_requires_login(self):
        """Anonymous users are redirected to login."""
        self.client.logout()
        response = self._get({"q": "auto"})
        self.assertIn(response.status_code, (301, 302))

    def test_non_htmx_redirects_to_browse(self):
        """A plain browser GET redirects to the browse page."""
        response = self._get({"q": "auto"}, htmx=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("browse"), response.url)

    def test_non_htmx_redirect_keeps_query(self):
        """The browse redirect preserves the search term."""
        response = self._get({"q": "auto"}, htmx=False)
        self.assertIn("q=auto", response.url)

    def test_empty_term_returns_hidden_dropdown(self):
        """Missing or empty q renders the empty dropdown shell."""
        response = self._get()
        self.assertContains(response, 'id="suggestions-dropdown"')
        self.assertContains(response, "hidden")
        self.assertNotContains(response, "No matching words.")

        response = self._get({"q": "   "})
        self.assertContains(response, "hidden")

    # -- matching and ranking ---------------------------------------------------

    def test_one_letter_prefix_matches(self):
        """Typing one letter already suggests matching words."""
        Word.objects.create(dutch="auto", translation="car", source="UK")
        response = self._get({"q": "a"})
        self.assertContains(response, ">auto</span>")

    def test_ranking_prefers_exact_then_prefix_then_contains(self):
        """Exact matches rank above prefixes above substring matches."""
        Word.objects.create(dutch="tankauto", translation="tank truck", source="UK")
        Word.objects.create(dutch="auto", translation="car", source="UK")
        Word.objects.create(dutch="autobus", translation="bus", source="UK")

        response = self._get({"q": "auto"})
        html = response.content.decode()
        exact_at = html.find(">auto</span>")
        prefix_at = html.find(">autobus</span>")
        contains_at = html.find(">tankauto</span>")
        self.assertGreater(exact_at, -1)
        self.assertGreater(prefix_at, exact_at)
        self.assertGreater(contains_at, prefix_at)

    def test_matches_translation_field(self):
        """Suggestions also match against the translation."""
        Word.objects.create(dutch="fiets", translation="bicycle", source="UK")
        response = self._get({"q": "bicycl"})
        self.assertContains(response, ">fiets</span>")

    def test_source_filter_respected(self):
        """The source filter limits suggestions to that source."""
        Word.objects.create(dutch="auto", translation="car", source="UK")
        Word.objects.create(dutch="auto", translation="car", source="EN")

        uk_only = self._get({"q": "auto", "source": "UK"})
        self.assertEqual(uk_only.content.decode().count('role="option"'), 1)

        en_only = self._get({"q": "auto", "source": "EN"})
        self.assertContains(en_only, ">auto</span>")
        self.assertEqual(en_only.content.decode().count('role="option"'), 1)

    def test_suggestions_capped_at_eight(self):
        """More than 8 matches are truncated to 8 suggestions."""
        for i in range(10):
            Word.objects.create(dutch=f"lamp{i}", translation=f"lamp number {i}", source="UK")
        response = self._get({"q": "lamp"})
        self.assertEqual(response.content.decode().count('role="option"'), 8)

    def test_no_matches_message(self):
        """A search with no hits shows the empty-state message."""
        Word.objects.create(dutch="auto", translation="car", source="UK")
        response = self._get({"q": "zzz"})
        self.assertContains(response, "No matching words.")
