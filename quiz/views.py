"""Views for the quiz app."""

import random
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress
from words.models import Flashcard, Word

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


@login_required
def start_quiz(request: HttpRequest, quiz_type: str) -> HttpResponse:
    """Start a new quiz session."""
    flashcards = Flashcard.objects.filter(user=request.user)

    if not flashcards.exists():
        return redirect("browse")

    word_ids = list(flashcards.values_list("word_id", flat=True))
    random.shuffle(word_ids)

    session = QuizSession.objects.create(user=request.user, quiz_type=quiz_type, total=10)

    request.session["quiz_word_ids"] = word_ids[:10]
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

    # Build multiple choice options from the word pool
    other_word_ids = [wid for wid in word_ids if wid != word_id]
    if len(other_word_ids) >= 3:
        wrong_word_ids = random.sample(other_word_ids, 3)
        wrong_words: QuerySet[Word] = Word.objects.filter(id__in=wrong_word_ids)
    else:
        wrong_words = Word.objects.filter(id__in=other_word_ids)

    options = list(wrong_words) + [word]
    random.shuffle(options)

    # Get quiz type display name
    session_id = request.session.get("quiz_session_id")
    quiz_type_display = ""
    if session_id:
        try:
            session = QuizSession.objects.get(id=session_id)
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

    word_id = request.POST.get("word_id")
    answer_id = request.POST.get("answer_id")

    if not word_id or not answer_id:
        return redirect("quiz_home")

    word = get_object_or_404(Word, id=word_id)

    # Handle case where answer word might not exist (e.g., was deleted)
    try:
        answer_word = Word.objects.get(id=answer_id)
        user_answer_text = answer_word.translation
    except Word.DoesNotExist:
        user_answer_text = f"Unknown word (ID: {answer_id})"

    is_correct = answer_id == word_id

    session_id = request.session.get("quiz_session_id")
    if not session_id:
        return redirect("quiz_home")
    session = get_object_or_404(QuizSession, id=session_id)

    QuizAnswer.objects.create(
        session=session,
        word=word,
        user_answer=user_answer_text,
        is_correct=is_correct,
    )

    if is_correct:
        request.session["quiz_score"] = request.session.get("quiz_score", 0) + 1

    request.session["quiz_current"] = request.session.get("quiz_current", 0) + 1

    return redirect("quiz_question")


@login_required
def quiz_results(request: HttpRequest) -> HttpResponse:
    """Show the results of a completed quiz and update progress."""
    session_id = request.session.get("quiz_session_id")
    if not session_id:
        return redirect("dashboard")

    session = get_object_or_404(QuizSession, id=session_id)

    score = request.session.get("quiz_score", 0)
    total = session.total

    session.score = score
    session.completed_at = timezone.now()
    session.save()

    # Update user progress
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    progress.total_quizzes += 1

    previous_total = progress.total_quizzes - 1
    total_score = progress.average_score * previous_total + score if previous_total > 0 else score
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
        "percentage": int((score / total) * 100) if total > 0 else 0,
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
