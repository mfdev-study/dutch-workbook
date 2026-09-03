"""Views for the quiz app."""

import random
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress
from words.models import Flashcard, Word, WordRelation

from .models import QuizAnswer, QuizSession


@login_required
def quiz_home(request: HttpRequest) -> HttpResponse:
    """Show the quiz type selection page."""
    flashcards = Flashcard.objects.filter(user=request.user)
    word_count = flashcards.count()

    context: dict[str, Any] = {
        "word_count": word_count,
    }
    return render(request, "quiz/home.html", context)


MAX_QUIZ_SIZE = 10


@login_required
def start_quiz(request: HttpRequest, quiz_type: str) -> HttpResponse:
    """Start a new quiz session."""
    if quiz_type not in QuizSession.QuizType.values:
        return redirect("quiz_home")

    flashcards = Flashcard.objects.filter(user=request.user)

    if not flashcards.exists():
        return redirect("browse")

    word_ids = list(flashcards.values_list("word_id", flat=True))
    random.shuffle(word_ids)
    word_ids = word_ids[:MAX_QUIZ_SIZE]

    session = QuizSession.objects.create(
        user=request.user, quiz_type=quiz_type, total=len(word_ids)
    )

    request.session["quiz_word_ids"] = word_ids
    request.session["quiz_current"] = 0
    request.session["quiz_score"] = 0
    request.session["quiz_session_id"] = session.id

    return redirect("quiz_question")


@login_required
def quiz_question(request: HttpRequest) -> HttpResponse:
    """Show the current quiz question."""
    word_ids: list[int] = request.session.get("quiz_word_ids", [])
    current: int = request.session.get("quiz_current", 0)
    score: int = request.session.get("quiz_score", 0)

    if current >= len(word_ids):
        return redirect("quiz_results")

    word_id = word_ids[current]
    word = get_object_or_404(Word, id=word_id)

    # Build multiple choice options — prefer semantically related words as distractors
    other_word_ids = [wid for wid in word_ids if wid != word_id]

    related_ids = list(
        WordRelation.objects.filter(
            word_from_id=word_id,
        )
        .exclude(word_to_id=word_id)
        .values_list("word_to_id", flat=True)
    ) + list(
        WordRelation.objects.filter(
            word_to_id=word_id,
        )
        .exclude(word_from_id=word_id)
        .values_list("word_from_id", flat=True)
    )
    related_ids = [rid for rid in related_ids if rid in other_word_ids]

    wrong_word_ids = []
    remaining_ids = [wid for wid in other_word_ids if wid not in related_ids]

    if len(related_ids) >= 3:
        wrong_word_ids = random.sample(related_ids, 3)
    elif len(related_ids) > 0:
        wrong_word_ids = list(related_ids)
        needed = 3 - len(wrong_word_ids)
        if len(remaining_ids) >= needed:
            wrong_word_ids.extend(random.sample(remaining_ids, needed))
        else:
            wrong_word_ids.extend(remaining_ids)
    else:
        if len(other_word_ids) >= 3:
            wrong_word_ids = random.sample(other_word_ids, 3)
        else:
            wrong_word_ids = list(other_word_ids)

    wrong_words: QuerySet[Word] = Word.objects.filter(id__in=wrong_word_ids)
    options = list(wrong_words) + [word]
    random.shuffle(options)

    # Get quiz type display name
    session_id = request.session.get("quiz_session_id")
    quiz_type_display = ""
    if session_id:
        try:
            session = QuizSession.objects.get(id=session_id, user=request.user)
            quiz_type_display = session.get_quiz_type_display()
        except QuizSession.DoesNotExist:
            pass

    context: dict[str, Any] = {
        "word": word,
        "options": options,
        "question_num": current + 1,
        "total": len(word_ids),
        "score": score,
        "quiz_type": quiz_type_display,
    }
    return render(request, "quiz/question.html", context)


@login_required
def submit_answer(request: HttpRequest) -> HttpResponse:
    """Submit an answer to the current quiz question."""
    if request.method != "POST":
        return redirect("quiz_home")

    session_id = request.session.get("quiz_session_id")
    if not session_id:
        return redirect("quiz_home")
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)

    word_ids: list[int] = request.session.get("quiz_word_ids", [])
    current: int = request.session.get("quiz_current", 0)

    if current >= len(word_ids):
        return redirect("quiz_results")

    word_id = word_ids[current]
    word = get_object_or_404(Word, id=word_id)

    answer_id = request.POST.get("answer_id")
    if not answer_id:
        return redirect("quiz_question")

    try:
        answer_id = int(answer_id)
    except (TypeError, ValueError):
        return redirect("quiz_question")

    # Handle case where answer word might not exist (e.g., was deleted)
    try:
        answer_word = Word.objects.get(id=answer_id)
        user_answer_text = answer_word.translation
    except Word.DoesNotExist:
        user_answer_text = f"Unknown word (ID: {answer_id})"

    is_correct = answer_id == word_id

    QuizAnswer.objects.create(
        session=session,
        word=word,
        user_answer=user_answer_text,
        is_correct=is_correct,
    )

    if is_correct:
        request.session["quiz_score"] = request.session.get("quiz_score", 0) + 1

    request.session["quiz_current"] = current + 1

    return redirect("quiz_question")


@login_required
def quiz_results(request: HttpRequest) -> HttpResponse:
    """Show the results of a completed quiz and update progress."""
    session_id = request.session.get("quiz_session_id")
    if not session_id:
        return redirect("dashboard")

    session = get_object_or_404(QuizSession, id=session_id, user=request.user)

    score = request.session.get("quiz_score", 0)
    total = session.total

    session.score = score
    session.completed_at = timezone.now()
    session.save()

    percentage = (score / total) * 100 if total > 0 else 0.0

    # Update user progress
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    progress.total_quizzes += 1

    previous_total = progress.total_quizzes - 1
    total_score = (
        progress.average_score * previous_total + percentage if previous_total > 0 else percentage
    )
    progress.average_score = total_score / progress.total_quizzes
    progress.save()

    # Record daily activity
    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
    daily.quizzes_completed += 1
    answers = QuizAnswer.objects.filter(session=session)
    daily.correct_answers += answers.filter(is_correct=True).count()
    daily.total_answers += answers.count()
    daily.save()

    # Clean up session keys
    for key in ["quiz_word_ids", "quiz_current", "quiz_score", "quiz_session_id"]:
        request.session.pop(key, None)

    context: dict[str, Any] = {
        "session": session,
        "score": score,
        "total": total,
        "percentage": int(percentage),
    }
    return render(request, "quiz/results.html", context)


@login_required
def quiz_history(request: HttpRequest) -> HttpResponse:
    """Show the user's quiz history."""
    sessions = QuizSession.objects.filter(user=request.user, completed_at__isnull=False).order_by(
        "-started_at"
    )[:50]

    context: dict[str, Any] = {
        "sessions": sessions,
    }
    return render(request, "quiz/history.html", context)
