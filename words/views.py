"""Views for the words (vocabulary) app."""

import logging
import threading
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress

from .models import Example, Flashcard, Word, WordList
from .services.word_generation import (  # noqa: F401  # Used by tests via mock
    WordGenerationRequest,
    WordGenerationService,
)

logger = logging.getLogger(__name__)


def _get_favorite_list(user) -> WordList:
    """Get or create the user's Favorites word list."""
    favorite_list, _ = WordList.objects.get_or_create(
        user=user,
        name="Favorites",
        defaults={"list_type": WordList.ListType.FAVORITES},
    )
    return favorite_list


def _record_word_learned(user) -> None:
    """Increment words_learned counter and daily activity."""
    progress, _ = UserProgress.objects.get_or_create(user=user)
    progress.words_learned += 1
    progress.save()

    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=user, date=today)
    daily.new_words += 1
    daily.save()


@login_required
def add_word(request: HttpRequest) -> HttpResponse:
    """Add a new Dutch word to the vocabulary."""
    if request.method == "POST":
        dutch = request.POST.get("dutch", "").strip()
        translation = request.POST.get("translation", "").strip()
        source = request.POST.get("source", "EN")
        context = request.POST.get("context", "").strip()
        example = request.POST.get("example", "").strip()

        if dutch and translation:
            word, created = Word.objects.get_or_create(
                dutch=dutch,
                translation=translation,
                source=source,
                defaults={
                    "context": context,
                    "example": example,
                },
            )
            if created:
                Flashcard.objects.create(
                    user=request.user,
                    word=word,
                    box=Flashcard.Box.BOX_1,
                    next_review=timezone.now(),
                )
                _record_word_learned(request.user)
                return redirect("word_detail", word_id=word.id)

    return render(request, "words/add_word.html")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Show the main dashboard with learning stats."""
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)

    flashcards = Flashcard.objects.filter(user=request.user)
    due_cards = flashcards.filter(next_review__lte=timezone.now())
    favorite_list = _get_favorite_list(request.user)

    context: dict[str, Any] = {
        "progress": progress,
        "due_cards_count": due_cards.count(),
        "total_cards": flashcards.count(),
        "favorite_count": favorite_list.words.count(),
        "daily": daily,
    }
    return render(request, "words/dashboard.html", context)


@login_required
def browse_words(request: HttpRequest) -> HttpResponse:
    """Browse and search the word bank."""
    query = request.GET.get("q", "").strip()
    source = request.GET.get("source", "")

    words: QuerySet[Word] = Word.objects.all()

    if query:
        words = words.filter(Q(dutch__icontains=query) | Q(translation__icontains=query))

    if source:
        words = words.filter(source=source)

    words = words[:100]

    favorite_list = _get_favorite_list(request.user)
    favorites_ids = list(favorite_list.words.values_list("id", flat=True))

    context: dict[str, Any] = {
        "words": words,
        "query": query,
        "source": source,
        "favorites_ids": favorites_ids,
    }
    return render(request, "words/browse.html", context)


@login_required
def word_detail(request: HttpRequest, word_id: int) -> HttpResponse:
    """Show details for a single word."""
    word = get_object_or_404(Word, id=word_id)

    has_flashcard = Flashcard.objects.filter(user=request.user, word=word).exists()
    favorite_list = _get_favorite_list(request.user)
    is_favorite = favorite_list.words.filter(id=word_id).exists()

    context: dict[str, Any] = {
        "word": word,
        "has_flashcard": has_flashcard,
        "is_favorite": is_favorite,
    }
    return render(request, "words/detail.html", context)


@login_required
def add_flashcard(request: HttpRequest, word_id: int) -> HttpResponse:
    """Add a word to the user's flashcards."""
    word = get_object_or_404(Word, id=word_id)

    _, created = Flashcard.objects.get_or_create(
        user=request.user,
        word=word,
        defaults={
            "box": Flashcard.Box.BOX_1,
            "next_review": timezone.now(),
        },
    )

    if created:
        _record_word_learned(request.user)

    return redirect("word_detail", word_id=word_id)


@login_required
def remove_flashcard(request: HttpRequest, word_id: int) -> HttpResponse:
    """Remove a word from the user's flashcards."""
    word = get_object_or_404(Word, id=word_id)
    Flashcard.objects.filter(user=request.user, word=word).delete()
    return redirect("word_detail", word_id=word_id)


@login_required
def toggle_favorite(request: HttpRequest, word_id: int) -> HttpResponse:
    """Toggle the favorite status of a word."""
    word = get_object_or_404(Word, id=word_id)
    favorite_list = _get_favorite_list(request.user)

    if favorite_list.words.filter(id=word_id).exists():
        favorite_list.words.remove(word)
    else:
        favorite_list.words.add(word)

    return redirect("word_detail", word_id=word_id)


@login_required
def flashcards_review(request: HttpRequest) -> HttpResponse:
    """Show the flashcard review interface."""
    due_cards = (
        Flashcard.objects.filter(user=request.user, next_review__lte=timezone.now())
        .select_related("word")
        .order_by("next_review")
    )

    if not due_cards.exists():
        return render(request, "words/no_cards.html")

    current_card = due_cards.first()
    remaining_count = due_cards.count()

    intervals: dict[int, int] = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
    box = current_card.box
    next_box_hard = max(box, 2)
    next_box_good = min(box + 1, 5)
    next_box_easy = min(box + 2, 5)

    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
    daily.words_reviewed += 1
    daily.save()

    context: dict[str, Any] = {
        "card": current_card,
        "remaining_count": remaining_count,
        "total_due": remaining_count,
        "again_interval": 1,
        "hard_interval": intervals.get(next_box_hard, 1),
        "good_interval": intervals.get(next_box_good, 1),
        "easy_interval": intervals.get(next_box_easy, 1),
    }
    return render(request, "words/review.html", context)


@login_required
def rate_card(request: HttpRequest, card_id: int, rating: str) -> HttpResponse:
    """Rate a flashcard after review (spaced repetition)."""
    card = get_object_or_404(Flashcard, id=card_id, user=request.user)

    intervals: dict[int, int] = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

    if rating == "again":
        card.box = Flashcard.Box.BOX_1
        card.next_review = timezone.now() + timedelta(days=1)
    elif rating == "hard":
        card.box = max(card.box, Flashcard.Box.BOX_2.value)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
    elif rating == "good":
        card.box = min(card.box + 1, Flashcard.Box.BOX_5.value)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
    elif rating == "easy":
        card.box = min(card.box + 2, Flashcard.Box.BOX_5.value)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))

    else:
        return redirect("flashcards")

    card.last_reviewed = timezone.now()
    card.save()

    return redirect("flashcards")


@login_required
def favorites_list(request: HttpRequest) -> HttpResponse:
    """Show the user's favorite words."""
    favorite_list = _get_favorite_list(request.user)
    words = favorite_list.words.all()

    context: dict[str, Any] = {
        "list": favorite_list,
        "words": words,
    }
    return render(request, "words/favorites.html", context)


@login_required
def add_example(request: HttpRequest, word_id: int) -> HttpResponse:
    """Add an example sentence for a word."""
    word = get_object_or_404(Word, id=word_id)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        translation = request.POST.get("translation", "").strip()

        if text:
            Example.objects.create(
                word=word, text=text, translation=translation, created_by=request.user
            )
            return redirect("word_detail", word_id=word_id)

    context: dict[str, Any] = {
        "word": word,
    }
    return render(request, "words/add_example.html", context)


@login_required
def edit_example(request: HttpRequest, example_id: int) -> HttpResponse:
    """Edit an existing example sentence."""
    example = get_object_or_404(Example, id=example_id, created_by=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        translation = request.POST.get("translation", "").strip()

        if text:
            example.text = text
            example.translation = translation
            example.save()
            return redirect("word_detail", word_id=example.word.id)

    context: dict[str, Any] = {
        "example": example,
    }
    return render(request, "words/edit_example.html", context)


@login_required
def delete_example(request: HttpRequest, example_id: int) -> HttpResponse:
    """Delete an example sentence."""
    example = get_object_or_404(Example, id=example_id, created_by=request.user)

    if request.method == "POST":
        word_id = example.word.id
        example.delete()
        return redirect("word_detail", word_id=word_id)

    context: dict[str, Any] = {
        "example": example,
    }
    return render(request, "words/delete_example.html", context)


@login_required
def generate_words_view(request: HttpRequest) -> HttpResponse:
    """AI word generation with async polling support."""
    result_key = f"gen_result_{request.user.id}"

    # AJAX polling endpoint
    if request.GET.get("check") == "true":
        return _handle_generation_poll(result_key)

    # Base context
    context: dict[str, Any] = {
        "opencode_enabled": settings.OPENCODE_ENABLED,
        "levels": ["A1", "A2", "B1", "B2", "C1"],
        "sources": [("EN", "English"), ("RU", "Russian"), ("UK", "Ukrainian")],
    }

    # Check for completed results
    result = cache.get(result_key)
    if result and "word_ids" in result and "error" not in result:
        word_ids = result.get("word_ids", [])
        if word_ids:
            created_words = Word.objects.filter(id__in=word_ids)
            if created_words.exists():
                context["words_created"] = created_words
                context["words_skipped"] = result.get("words_skipped", 0)
                context["model_used"] = result.get("model_used", "unknown")
                cache.delete(result_key)
                return render(request, "words/generate_words.html", context)

    # Handle form submission
    if request.method == "POST":
        if not settings.OPENCODE_ENABLED:
            context["error"] = "OpenCode is not enabled."
            return render(request, "words/generate_words.html", context)

        try:
            count = int(request.POST.get("count", 5))
        except (ValueError, TypeError):
            count = 5
        level = request.POST.get("level", "A2")
        theme = request.POST.get("theme", "").strip() or None
        source = request.POST.get("source", "EN")

        cache.set(result_key, {"status": "generating"}, timeout=300)

        thread = threading.Thread(
            target=_generate_words_async,
            args=(
                request.user.id,
                count,
                level,
                theme,
                source,
                result_key,
            ),
            daemon=True,
        )
        thread.start()

        return redirect("generate_words")

    # Show generating state if in progress
    result = cache.get(result_key)
    if result is not None and "word_ids" not in result and "error" not in result:
        context["generating"] = True

    return render(request, "words/generate_words.html", context)


def _handle_generation_poll(result_key: str) -> JsonResponse:
    """Handle AJAX polling for generation status."""
    result = cache.get(result_key)
    if result:
        if "error" in result:
            return JsonResponse({"status": "error", "message": result["error"]})
        if "word_ids" in result:
            return JsonResponse(
                {
                    "status": "done",
                    "word_ids": result.get("word_ids", []),
                    "words_skipped": result.get("words_skipped", 0),
                    "model_used": result.get("model_used", "unknown"),
                }
            )
        return JsonResponse({"status": "pending"})
    return JsonResponse({"status": "pending"})


def _generate_words_async(
    user_id: int,
    count: int,
    level: str,
    theme: str | None,
    source: str,
    result_key: str,
) -> None:
    """Run word generation in a background thread."""
    try:
        import os

        os.environ["DJANGO_SETTINGS_MODULE"] = "nederlandse_workbook.settings"
        import django

        django.setup()

        # Thread-safe imports
        from django.core.cache import cache as thread_cache

        from words.services.word_generation import (
            WordGenerationRequest,
            WordGenerationService,
        )

        service = WordGenerationService()
        request_data = WordGenerationRequest(
            count=count,
            level=level,
            theme=theme,
            source=source,
        )
        used_model, generated_words = service.generate_words(request_data)

        if not generated_words:
            thread_cache.set(result_key, {"error": "Could not parse AI response."}, timeout=300)
            return

        created, skipped = service.save_words(generated_words, source)
        result_data = {
            "word_ids": [w.id for w in created],
            "words_skipped": len(skipped),
            "model_used": used_model,
        }
        thread_cache.set(result_key, result_data, timeout=300)
    except Exception as e:
        logger.exception("Error in background word generation")
        from django.core.cache import cache as thread_cache

        thread_cache.set(result_key, {"error": str(e)}, timeout=300)
