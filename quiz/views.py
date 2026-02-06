import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from progress.models import DailyActivity, UserProgress
from words.models import Flashcard, Word

from .models import QuizAnswer, QuizSession


@login_required
def quiz_home(request):
    flashcards = Flashcard.objects.filter(user=request.user)
    word_count = flashcards.count()

    context = {
        "word_count": word_count,
    }
    return render(request, "quiz/home.html", context)


@login_required
def start_quiz(request, quiz_type):
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
def quiz_question(request):
    word_ids = request.session.get("quiz_word_ids", [])
    current = request.session.get("quiz_current", 0)
    score = request.session.get("quiz_score", 0)

    if current >= len(word_ids):
        return redirect("quiz_results")

    word_id = word_ids[current]
    word = get_object_or_404(Word, id=word_id)

    wrong_words = Word.objects.exclude(id=word_id).order_by("?")[:3]
    options = list(wrong_words) + [word]
    random.shuffle(options)

    context = {
        "word": word,
        "options": options,
        "question_num": current + 1,
        "total": len(word_ids),
        "score": score,
        "quiz_type": request.session.get("quiz_session_id"),
    }
    return render(request, "quiz/question.html", context)


@login_required
def submit_answer(request):
    if request.method != "POST":
        return redirect("quiz_home")

    word_id = request.POST.get("word_id")
    answer_id = request.POST.get("answer_id")

    word = get_object_or_404(Word, id=word_id)
    answer_word = get_object_or_404(Word, id=answer_id)

    is_correct = answer_id == word_id

    session_id = request.session.get("quiz_session_id")
    session = get_object_or_404(QuizSession, id=session_id)

    QuizAnswer.objects.create(
        session=session,
        word=word,
        user_answer=answer_word.translation,
        is_correct=is_correct,
    )

    if is_correct:
        request.session["quiz_score"] = request.session.get("quiz_score", 0) + 1

    request.session["quiz_current"] = request.session.get("quiz_current", 0) + 1

    return redirect("quiz_question")


@login_required
def quiz_results(request):
    session_id = request.session.get("quiz_session_id")
    if not session_id:
        return redirect("dashboard")

    session = get_object_or_404(QuizSession, id=session_id)

    score = request.session.get("quiz_score", 0)
    total = session.total

    session.score = score
    session.completed_at = timezone.now()
    session.save()

    progress, created = UserProgress.objects.get_or_create(user=request.user)
    progress.total_quizzes += 1

    total_score = (
        (progress.average_score * (progress.total_quizzes - 1)) + score
        if progress.total_quizzes > 0
        else score
    )
    progress.average_score = total_score / progress.total_quizzes
    progress.save()

    today = timezone.now().date()
    daily, _ = DailyActivity.objects.get_or_create(user=request.user, date=today)
    daily.quizzes_completed += 1
    answers = QuizAnswer.objects.filter(session=session)
    daily.correct_answers += answers.filter(is_correct=True).count()
    daily.total_answers += answers.count()
    daily.save()

    del request.session["quiz_word_ids"]
    del request.session["quiz_current"]
    del request.session["quiz_score"]
    del request.session["quiz_session_id"]

    context = {
        "session": session,
        "score": score,
        "total": total,
        "percentage": int((score / total) * 100) if total > 0 else 0,
    }
    return render(request, "quiz/results.html", context)


@login_required
def quiz_history(request):
    sessions = QuizSession.objects.filter(user=request.user, completed_at__isnull=False).order_by(
        "-started_at"
    )[:50]

    context = {
        "sessions": sessions,
    }
    return render(request, "quiz/history.html", context)
