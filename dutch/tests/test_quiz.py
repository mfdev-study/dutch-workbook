"""Tests for the Dutch de/het article quiz."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from dutch.models import DutchArticleQuestion
from dutch.views import QUIZ_SIZE, SESSION_KEY

User = get_user_model()


def _question(**kwargs):
    defaults = {
        "word": "appel",
        "translation": "apple",
        "correct_article": "de",
        "explanation": "Test explanation.",
        "category": "memorize",
        "level": "A1",
        "is_active": True,
    }
    defaults.update(kwargs)
    return DutchArticleQuestion.objects.create(**defaults)


class DutchArticleQuestionModelTest(TestCase):
    """Model creation and validation."""

    def test_question_can_be_created(self):
        q = _question(word="kinderen", correct_article="de", category="plural")
        self.assertEqual(q.word, "kinderen")
        self.assertEqual(q.correct_article, "de")
        self.assertEqual(q.category, "plural")
        self.assertTrue(q.is_active)

    def test_str_returns_article_and_word(self):
        q = _question(word="huis", correct_article="het")
        self.assertEqual(str(q), "het huis")

    def test_valid_question_clean_passes(self):
        q = _question(word="boeken", correct_article="de", category="plural")
        q.clean()
        self.assertIsNone(q.clean())

    def test_clean_rejects_invalid_article(self):
        q = _question(correct_article="der")
        with self.assertRaises(ValidationError):
            q.clean()

    def test_clean_rejects_empty_word(self):
        q = _question(word="  ")
        with self.assertRaises(ValidationError):
            q.clean()

    def test_clean_rejects_invalid_category(self):
        q = _question(category="bogus")
        with self.assertRaises(ValidationError):
            q.clean()

    def test_clean_rejects_invalid_level(self):
        q = _question(level="B2")
        with self.assertRaises(ValidationError):
            q.clean()


class DutchArticleAnswerValidationTest(TestCase):
    """Backend answer validation for the documented article rules."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")
        self.kinderen = _question(
            word="kinderen",
            correct_article="de",
            category="plural",
            explanation="Kinderen is a plural noun, so it uses de.",
        )
        self.huisje = _question(
            word="huisje",
            correct_article="het",
            category="diminutive",
            explanation="Diminutives ending in -je take het.",
        )
        self.regering = _question(
            word="regering",
            correct_article="de",
            category="ing",
            explanation="Nouns ending in -ing take de.",
        )
        self.gezondheid = _question(
            word="gezondheid",
            correct_article="de",
            category="heid",
            explanation="Nouns ending in -heid take de.",
        )

    def _start_quiz(self, questions):
        state = {
            "question_ids": [q.id for q in questions],
            "current": 0,
            "answers": [],
            "score": 0,
        }
        session = self.client.session
        session[SESSION_KEY] = state
        session.save()

    def _post(self, question, answer):
        return self.client.post(
            reverse("dutch:answer"),
            {"question_id": question.id, "answer": answer},
        )

    def _session_answers(self):
        return self.client.session[SESSION_KEY]["answers"]

    def test_de_kinderen_correct(self):
        self._start_quiz([self.kinderen])
        self.assertEqual(self._post(self.kinderen, "de").status_code, 200)
        self.assertTrue(self._session_answers()[0]["is_correct"])

    def test_het_kinderen_incorrect(self):
        self._start_quiz([self.kinderen])
        self._post(self.kinderen, "het")
        self.assertFalse(self._session_answers()[0]["is_correct"])

    def test_het_huisje_correct(self):
        self._start_quiz([self.huisje])
        self._post(self.huisje, "het")
        self.assertTrue(self._session_answers()[0]["is_correct"])

    def test_de_huisje_incorrect(self):
        self._start_quiz([self.huisje])
        self._post(self.huisje, "de")
        self.assertFalse(self._session_answers()[0]["is_correct"])

    def test_de_regering_correct(self):
        self._start_quiz([self.regering])
        self._post(self.regering, "de")
        self.assertTrue(self._session_answers()[0]["is_correct"])

    def test_het_regering_incorrect(self):
        self._start_quiz([self.regering])
        self._post(self.regering, "het")
        self.assertFalse(self._session_answers()[0]["is_correct"])

    def test_de_gezondheid_correct(self):
        self._start_quiz([self.gezondheid])
        self._post(self.gezondheid, "de")
        self.assertTrue(self._session_answers()[0]["is_correct"])

    def test_het_gezondheid_incorrect(self):
        self._start_quiz([self.gezondheid])
        self._post(self.gezondheid, "het")
        self.assertFalse(self._session_answers()[0]["is_correct"])

    def test_answer_feedback_lists_article_and_explanation(self):
        self._start_quiz([self.kinderen])
        response = self._post(self.kinderen, "het")
        self.assertContains(response, "Not quite")
        self.assertContains(response, "de kinderen")
        self.assertContains(response, "plural")


class DutchArticleQuizFlowTest(TestCase):
    """Quiz session selection and progression."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")
        # 15 seeded questions exist from the data migration; add a few extras.

    def _start(self):
        response = self.client.get(reverse("dutch:quiz"))
        self.assertEqual(response.status_code, 200)
        return self.client.session[SESSION_KEY]

    def test_selects_exactly_five_questions(self):
        state = self._start()
        self.assertEqual(len(state["question_ids"]), QUIZ_SIZE)

    def test_no_duplicate_questions(self):
        state = self._start()
        self.assertEqual(len(state["question_ids"]), len(set(state["question_ids"])))

    def test_inactive_questions_are_not_selected(self):
        target = DutchArticleQuestion.objects.filter().first()
        target.is_active = False
        target.save()
        state = self._start()
        self.assertNotIn(target.id, state["question_ids"])

    def test_questions_come_from_different_categories_when_possible(self):
        state = self._start()
        questions = DutchArticleQuestion.objects.filter(id__in=state["question_ids"])
        categories = set(questions.values_list("category", flat=True))
        self.assertGreater(len(categories), 1)

    def test_score_is_calculated_correctly(self):
        state = self._start()
        question = DutchArticleQuestion.objects.get(id=state["question_ids"][0])
        session = self.client.session
        session[SESSION_KEY] = {
            "question_ids": [question.id],
            "current": 0,
            "answers": [],
            "score": 0,
        }
        session.save()
        response = self.client.post(
            reverse("dutch:answer"),
            {"question_id": question.id, "answer": question.correct_article},
        )
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertEqual(session[SESSION_KEY]["score"], 1)
        self.assertEqual(session[SESSION_KEY]["current"], 1)

    def test_result_page_displays_score(self):
        self._start()
        session = self.client.session
        session[SESSION_KEY]["question_ids"] = session[SESSION_KEY]["question_ids"][:2]
        session.save()
        for question_id in session[SESSION_KEY]["question_ids"][:2]:
            question = DutchArticleQuestion.objects.get(id=question_id)
            self.client.post(
                reverse("dutch:answer"),
                {"question_id": question.id, "answer": question.correct_article},
            )
        response = self.client.get(reverse("dutch:result"))
        self.assertContains(response, "2 / 2")
        self.assertContains(response, "100%")

    def test_new_quiz_resets_previous_session(self):
        self._start()
        session = self.client.session
        old_ids = session[SESSION_KEY]["question_ids"]
        response = self.client.get(reverse("dutch:reset"))
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertNotEqual(session[SESSION_KEY]["question_ids"], old_ids)
        self.assertEqual(session[SESSION_KEY]["current"], 0)
        self.assertEqual(session[SESSION_KEY]["answers"], [])

    def test_quiz_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dutch:quiz"))
        self.assertIn(response.status_code, (302, 403))
        self.assertIn("/accounts/login/", response.get("Location", ""))


class DutchArticleSecurityTest(TestCase):
    """The client must not be able to manipulate the correct answer."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")
        self.question = _question(word="kinderen", correct_article="de", category="plural")

    def _start(self):
        session = self.client.session
        session[SESSION_KEY] = {
            "question_ids": [self.question.id],
            "current": 0,
            "answers": [],
            "score": 0,
        }
        session.save()

    def test_spoofed_correct_article_does_not_change_result(self):
        self._start()
        self.client.post(
            reverse("dutch:answer"),
            {
                "question_id": self.question.id,
                "answer": "de",
                "correct_article": "het",  # client tries to lie
            },
        )
        answers = self.client.session[SESSION_KEY]["answers"]
        self.assertTrue(answers[0]["is_correct"])
        self.assertEqual(answers[0]["correct_article"], "de")
        fresh = DutchArticleQuestion.objects.get(id=self.question.id)
        self.assertEqual(fresh.correct_article, "de")

    def test_answer_not_matching_session_question_is_rejected(self):
        self._start()
        other = _question(word="huis", correct_article="het", category="memorize")
        response = self.client.post(
            reverse("dutch:answer"),
            {"question_id": other.id, "answer": "het"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session[SESSION_KEY]["current"], 0)

    def test_post_without_session_rejected(self):
        response = self.client.post(
            reverse("dutch:answer"), {"question_id": self.question.id, "answer": "de"}
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_answer_rejected(self):
        self._start()
        response = self.client.post(
            reverse("dutch:answer"),
            {"question_id": self.question.id, "answer": "der"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session[SESSION_KEY]["current"], 0)

    def test_get_on_answer_endpoint_rejected(self):
        self._start()
        response = self.client.get(reverse("dutch:answer"))
        self.assertEqual(response.status_code, 405)


class DutchArticleLocalizationTest(TestCase):
    """The de/het quiz UI is translated for supported locales."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        _question(word="huis", translation="house")

    def _page(self):
        return self.client.get(reverse("dutch:quiz")).content.decode()

    def test_ukrainian_translations_applied(self):
        with translation.override("uk"):
            doc = self._page()
        self.assertIn("Нідерландські артиклі", doc)
        self.assertIn("Питання", doc)
        self.assertIn("Рахунок:", doc)
        self.assertNotIn("Dutch Articles", doc)
        self.assertNotIn("Score:", doc)

    def test_russian_translations_applied(self):
        with translation.override("ru"):
            doc = self._page()
        self.assertIn("Нидерландские артикли", doc)
        self.assertIn("Вопрос", doc)
        self.assertIn("Счёт:", doc)

    def test_dutch_translations_applied(self):
        with translation.override("nl"):
            doc = self._page()
        self.assertIn("Nederlandse lidwoorden", doc)
        self.assertIn("Vraag", doc)
        self.assertIn("Score:", doc)

    def test_english_fallback_when_locale_unsupported(self):
        url = reverse("dutch:quiz")
        with translation.override("fr"):
            doc = self.client.get(url).content.decode()
        self.assertIn("Dutch Articles", doc)
        self.assertIn("Score:", doc)
