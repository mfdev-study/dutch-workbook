import re
from contextlib import suppress
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress

from .models import Category, Example, Flashcard, Word, WordList
from .services.word_generation import (
    WordGenerationRequest,
    WordGenerationService,
)


@login_required
def add_word(request):
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
                word.context = context
                word.example = example
                word.save()
                _ = Flashcard.objects.create(
                    user=request.user,
                    word=word,
                    box=1,
                    next_review=timezone.now(),
                )
                progress, _ = UserProgress.objects.get_or_create(user=request.user)
                progress.words_learned += 1
                progress.save()

                today = timezone.now().date()
                daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
                daily.new_words += 1
                daily.save()

                return redirect("word_detail", word_id=word.id)

    return render(request, "words/add_word.html")


@login_required
def dashboard(request):
    progress, created = UserProgress.objects.get_or_create(user=request.user)
    today = timezone.now().date()

    try:
        daily = DailyActivity.objects.get(user=request.user, date=today)
    except DailyActivity.DoesNotExist:
        daily = DailyActivity.objects.create(user=request.user, date=today)

    flashcards = Flashcard.objects.filter(user=request.user)
    due_cards = flashcards.filter(next_review__lte=timezone.now())

    favorite_list, _ = WordList.objects.get_or_create(
        user=request.user, name="Favorites", defaults={"list_type": "FAV"}
    )

    context = {
        "progress": progress,
        "due_cards_count": due_cards.count(),
        "total_cards": flashcards.count(),
        "favorite_count": favorite_list.words.count(),
        "daily": daily,
    }
    return render(request, "words/dashboard.html", context)


@login_required
def browse_words(request):
    query = request.GET.get("q", "")
    source = request.GET.get("source", "")

    words = Word.objects.all()

    if query:
        # For Cyrillic characters, use regex search for proper case insensitivity
        if any(ord(c) > 127 for c in query):  # Contains non-ASCII characters
            # Use regex for Cyrillic case insensitive search
            dutch_q = Q(dutch__regex=f"(?i){re.escape(query)}")
            translation_q = Q(translation__regex=f"(?i){re.escape(query)}")
            words = words.filter(dutch_q | translation_q)
        else:
            # Use standard icontains for ASCII characters
            words = words.filter(dutch__icontains=query) | words.filter(
                translation__icontains=query
            )

    if source:
        words = words.filter(source=source)

    words = words[:100]

    favorite_list, _ = WordList.objects.get_or_create(
        user=request.user, name="Favorites", defaults={"list_type": "FAV"}
    )

    favorites_ids = list(favorite_list.words.values_list("id", flat=True))

    context = {
        "words": words,
        "query": query,
        "source": source,
        "favorites_ids": favorites_ids,
    }
    return render(request, "words/browse.html", context)


@login_required
def word_detail(request, word_id):
    word = get_object_or_404(Word, id=word_id)

    has_flashcard = Flashcard.objects.filter(user=request.user, word=word).exists()

    favorite_list, _ = WordList.objects.get_or_create(
        user=request.user, name="Favorites", defaults={"list_type": "FAV"}
    )
    is_favorite = favorite_list.words.filter(id=word_id).exists()

    context = {
        "word": word,
        "has_flashcard": has_flashcard,
        "is_favorite": is_favorite,
    }
    return render(request, "words/detail.html", context)


@login_required
def add_flashcard(request, word_id):
    word = get_object_or_404(Word, id=word_id)

    flashcard, created = Flashcard.objects.get_or_create(
        user=request.user,
        word=word,
        defaults={
            "box": 1,
            "next_review": timezone.now(),
        },
    )

    if created:
        progress, _ = UserProgress.objects.get_or_create(user=request.user)
        progress.words_learned += 1
        progress.save()

        today = timezone.now().date()
        daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
        daily.new_words += 1
        daily.save()

    return redirect("word_detail", word_id=word_id)


@login_required
def remove_flashcard(request, word_id):
    word = get_object_or_404(Word, id=word_id)
    Flashcard.objects.filter(user=request.user, word=word).delete()
    return redirect("word_detail", word_id=word_id)


@login_required
def toggle_favorite(request, word_id):
    word = get_object_or_404(Word, id=word_id)

    favorite_list, _ = WordList.objects.get_or_create(
        user=request.user, name="Favorites", defaults={"list_type": "FAV"}
    )

    if favorite_list.words.filter(id=word_id).exists():
        favorite_list.words.remove(word)
    else:
        favorite_list.words.add(word)

    return redirect("word_detail", word_id=word_id)


@login_required
def flashcards_review(request):
    due_cards = Flashcard.objects.filter(
        user=request.user, next_review__lte=timezone.now()
    ).order_by("next_review")

    if not due_cards.exists():
        return render(request, "words/no_cards.html")

    # Get the first due card for review
    current_card = due_cards.first()
    remaining_count = due_cards.count()

    # Update daily activity
    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
    daily.words_reviewed += 1
    daily.save()

    context = {
        "card": current_card,
        "remaining_count": remaining_count,
        "total_due": remaining_count,
    }
    return render(request, "words/review.html", context)


@login_required
def rate_card(request, card_id, rating):
    card = get_object_or_404(Flashcard, id=card_id, user=request.user)

    intervals = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

    if rating == "again":
        card.box = 1
        card.next_review = timezone.now() + timedelta(days=1)
    elif rating == "hard":
        card.box = max(card.box, 2)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
    elif rating == "good":
        card.box = min(card.box + 1, 5)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
    elif rating == "easy":
        card.box = min(card.box + 2, 5)
        card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))

    card.last_reviewed = timezone.now()
    card.save()

    # Redirect back to review page to show next card
    return redirect("flashcards")


@login_required
def favorites_list(request):
    favorite_list, _ = WordList.objects.get_or_create(
        user=request.user, name="Favorites", defaults={"list_type": "FAV"}
    )

    words = favorite_list.words.all()

    context = {
        "list": favorite_list,
        "words": words,
    }
    return render(request, "words/favorites.html", context)


@login_required
def add_example(request, word_id):
    word = get_object_or_404(Word, id=word_id)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        translation = request.POST.get("translation", "").strip()

        if text:
            Example.objects.create(
                word=word, text=text, translation=translation, created_by=request.user
            )
            return redirect("word_detail", word_id=word_id)

    context = {
        "word": word,
    }
    return render(request, "words/add_example.html", context)


@login_required
def edit_example(request, example_id):
    example = get_object_or_404(Example, id=example_id, created_by=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        translation = request.POST.get("translation", "").strip()

        if text:
            example.text = text
            example.translation = translation
            example.save()
            return redirect("word_detail", word_id=example.word.id)

    context = {
        "example": example,
    }
    return render(request, "words/edit_example.html", context)


@login_required
def delete_example(request, example_id):
    example = get_object_or_404(Example, id=example_id, created_by=request.user)

    if request.method == "POST":
        word_id = example.word.id
        example.delete()
        return redirect("word_detail", word_id=word_id)

    context = {
        "example": example,
    }
    return render(request, "words/delete_example.html", context)


@login_required
def generate_words_view(request):
    """View for AI word generation interface."""
    context = {
        "opencode_enabled": settings.OPENCODE_ENABLED,
        "categories": Category.objects.all().order_by("name"),
        "levels": ["A1", "A2", "B1", "B2", "C1"],
        "sources": [("EN", "English"), ("RU", "Russian"), ("UK", "Ukrainian")],
    }

    if request.method == "POST":
        if not settings.OPENCODE_ENABLED:
            context["error"] = "OpenCode is not enabled. opencode-auto not found in PATH."
            return render(request, "words/generate_words.html", context)

        count = int(request.POST.get("count", 5))
        level = request.POST.get("level", "A2")
        theme = request.POST.get("theme", "").strip() or None
        source = request.POST.get("source", "EN")
        category_id = request.POST.get("category", "")

        category = None
        if category_id:
            with suppress(Category.DoesNotExist):
                category = Category.objects.get(id=category_id)

        request_data = WordGenerationRequest(
            count=count,
            level=level,
            theme=theme,
            source=source,
            category_name=category.name if category else None,
        )

        try:
            service = WordGenerationService()
            used_model, generated_words = service.generate_words(request_data)

            if not generated_words:
                context["error"] = "Could not parse AI response. Please try again."
                return render(request, "words/generate_words.html", context)

            created, skipped = service.save_words(generated_words, source, category)

            context["words_created"] = created
            context["words_skipped"] = skipped
            context["model_used"] = used_model

        except Exception as e:
            context["error"] = f"Error generating words: {str(e)}"

    return render(request, "words/generate_words.html", context)
