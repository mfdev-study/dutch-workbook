"""Views for the words (vocabulary) app."""

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress, update_streak

from .models import (
    Example,
    Flashcard,
    Word,
    WordGenerationJob,
    WordList,
    WordRelation,
)
from .services.word_generation import (  # noqa: F401  # Used by tests via mock
    WordGenerationRequest,
    WordGenerationService,
)


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
    update_streak(user)


@login_required
def add_word(request: HttpRequest) -> HttpResponse:
    """Add a new Dutch word to the vocabulary."""
    if request.method == "POST":
        dutch = request.POST.get("dutch", "").strip()
        translation = request.POST.get("translation", "").strip()
        source = request.POST.get("source", Word.Source.ENGLISH)
        context = request.POST.get("context", "").strip()
        example = request.POST.get("example", "").strip()

        if source not in Word.Source.values:
            source = Word.Source.ENGLISH

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

    paginator = Paginator(words, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    favorite_list = _get_favorite_list(request.user)
    favorites_ids = list(favorite_list.words.values_list("id", flat=True))

    context: dict[str, Any] = {
        "words": page_obj,
        "page_obj": page_obj,
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
    if request.method != "POST":
        return redirect("word_detail", word_id=word_id)

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
    if request.method != "POST":
        return redirect("word_detail", word_id=word_id)

    word = get_object_or_404(Word, id=word_id)
    Flashcard.objects.filter(user=request.user, word=word).delete()
    return redirect("word_detail", word_id=word_id)


@login_required
def toggle_favorite(request: HttpRequest, word_id: int) -> HttpResponse:
    """Toggle the favorite status of a word."""
    if request.method != "POST":
        return redirect("word_detail", word_id=word_id)

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

    related_words = current_card.word.related_words()
    user_word_ids = set(
        Flashcard.objects.filter(user=request.user).values_list("word_id", flat=True)
    )
    for rw in related_words:
        rw["has_flashcard"] = rw["word"].id in user_word_ids

    context: dict[str, Any] = {
        "card": current_card,
        "remaining_count": remaining_count,
        "total_due": remaining_count,
        "again_interval": 1,
        "hard_interval": intervals.get(next_box_hard, 1),
        "good_interval": intervals.get(next_box_good, 1),
        "easy_interval": intervals.get(next_box_easy, 1),
        "related_words": related_words,
    }
    return render(request, "words/review.html", context)


@login_required
def rate_card(request: HttpRequest, card_id: int, rating: str) -> HttpResponse:
    """Rate a flashcard after review (spaced repetition)."""
    if request.method != "POST":
        return redirect("flashcards")

    if rating not in ("again", "hard", "good", "easy"):
        return redirect("flashcards")

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

    card.last_reviewed = timezone.now()
    card.save()

    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
    daily.words_reviewed += 1
    daily.save()
    update_streak(request.user)

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
def learning_path(request: HttpRequest, word_id: int) -> HttpResponse:
    """Show a BFS-based learning path from a starting word through its relations."""
    start_word = get_object_or_404(Word, id=word_id)

    visited = {word_id}
    path_levels = []
    current_level = [word_id]
    user_word_ids = set(
        Flashcard.objects.filter(user=request.user).values_list("word_id", flat=True)
    )

    while current_level and len(path_levels) < 5:
        next_level = []
        level_words = []

        for wid in current_level:
            related = WordRelation.objects.filter(
                Q(word_from_id=wid) | Q(word_to_id=wid)
            ).select_related("word_from", "word_to")

            for r in related:
                neighbor_id = r.word_to_id if r.word_from_id == wid else r.word_from_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    next_level.append(neighbor_id)
                    word_obj = r.word_to if r.word_from_id == wid else r.word_from
                    label = r.get_relation_type_display()
                    level_words.append(
                        {
                            "word": word_obj,
                            "relation": label,
                            "has_flashcard": word_obj.id in user_word_ids,
                        }
                    )

        if level_words:
            path_levels.append(level_words)
        current_level = next_level

    context: dict[str, Any] = {
        "start_word": start_word,
        "path_levels": path_levels,
    }
    return render(request, "words/learning_path.html", context)


@login_required
def word_graph(request: HttpRequest) -> HttpResponse:
    """Show interactive lexical network graph."""
    return render(request, "words/graph.html")


@login_required
def word_graph_json(request: HttpRequest) -> JsonResponse:
    """Return JSON data for the lexical network graph."""
    flashcard_word_ids = list(
        Flashcard.objects.filter(user=request.user).values_list("word_id", flat=True)
    )

    if not flashcard_word_ids:
        return JsonResponse({"nodes": [], "edges": []})

    try:
        limit = int(request.GET.get("limit", 200))
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 1000))
    word_ids = flashcard_word_ids[:limit]
    word_id_set = set(word_ids)

    words = Word.objects.filter(id__in=word_ids)
    nodes = [
        {
            "id": w.id,
            "label": w.dutch,
            "title": f"{w.dutch} — {w.translation}",
            "group": w.part_of_speech or "other",
        }
        for w in words
    ]

    edges = []
    relations = WordRelation.objects.filter(
        Q(word_from_id__in=word_ids) & Q(word_to_id__in=word_ids)
    ).select_related("word_from", "word_to")

    color_map = {
        "SYN": {"color": "#22c55e", "label": "synonym"},
        "ANT": {"color": "#ef4444", "label": "antonym"},
        "HYP": {"color": "#3b82f6", "label": "hypernym"},
        "HPO": {"color": "#8b5cf6", "label": "hyponym"},
        "MER": {"color": "#f59e0b", "label": "meronym"},
        "HOL": {"color": "#ec4899", "label": "holonym"},
        "REL": {"color": "#6b7280", "label": "related"},
        "DER": {"color": "#14b8a6", "label": "derived"},
    }

    for r in relations:
        if r.word_from_id in word_id_set and r.word_to_id in word_id_set:
            style = color_map.get(r.relation_type, {"color": "#6b7280", "label": ""})
            edges.append(
                {
                    "from": r.word_from_id,
                    "to": r.word_to_id,
                    "label": style["label"],
                    "color": style["color"],
                    "arrows": "to",
                    "font": {"size": 10},
                }
            )

    return JsonResponse({"nodes": nodes, "edges": edges})


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

        # Rate limit: enforce a per-user cooldown between generation requests
        # and cap concurrent pending generations for the user.
        cooldown_key = f"gen_cooldown_{request.user.id}"
        retry_after = cache.get(cooldown_key)
        if retry_after is not None:
            remaining = retry_after - int(timezone.now().timestamp())
            context["error"] = "Please wait a moment before starting another generation."
            response = render(request, "words/generate_words.html", context)
            response["Retry-After"] = str(max(remaining, 0))
            response.status_code = 429
            return response
        pending = cache.get(result_key)
        if (
            pending is not None
            and isinstance(pending, dict)
            and "word_ids" not in pending
            and "error" not in pending
        ):
            context["error"] = "A generation is already in progress."
            response = render(request, "words/generate_words.html", context)
            response.status_code = 429
            return response

        try:
            count = int(request.POST.get("count", 5))
        except (ValueError, TypeError):
            count = 5
        count = max(1, min(count, 20))

        level = request.POST.get("level", "A2")
        if level not in ("A1", "A2", "B1", "B2", "C1"):
            level = "A2"

        theme = request.POST.get("theme", "").strip() or ""

        source = request.POST.get("source", Word.Source.ENGLISH)
        if source not in Word.Source.values:
            source = Word.Source.ENGLISH

        cache.set(result_key, {"status": "generating"}, timeout=300)
        cache.set(
            cooldown_key,
            int(timezone.now().timestamp()) + settings.GENERATION_COOLDOWN_SECONDS,
            timeout=settings.GENERATION_COOLDOWN_SECONDS + 5,
        )

        WordGenerationJob.objects.create(
            user=request.user,
            count=count,
            level=level,
            theme=theme,
            source=source,
        )

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
