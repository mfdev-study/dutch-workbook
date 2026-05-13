"""Views for the progress tracking app."""

from datetime import timedelta
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from quiz.models import QuizSession
from words.models import Flashcard

from .models import DailyActivity, UserProgress


@login_required
def progress_dashboard(request: HttpRequest) -> HttpResponse:
    """Show the user's learning progress dashboard."""
    progress, _ = UserProgress.objects.get_or_create(user=request.user)

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    daily_activities = DailyActivity.objects.filter(user=request.user, date__gte=week_ago).order_by(
        "date"
    )

    activity_data = {a.date: a for a in daily_activities}

    # Build chart data for the last 8 days
    chart_data: list[dict[str, Any]] = []
    for i in range(7, -1, -1):
        date = today - timedelta(days=i)
        if date in activity_data:
            activity = activity_data[date]
            chart_data.append(
                {
                    "date": date.strftime("%a"),
                    "reviews": activity.words_reviewed,
                    "quizzes": activity.quizzes_completed,
                }
            )
        else:
            chart_data.append(
                {
                    "date": date.strftime("%a"),
                    "reviews": 0,
                    "quizzes": 0,
                }
            )

    flashcards = Flashcard.objects.filter(user=request.user)

    # Build box distribution [Box1, Box2, Box3, Box4, Box5]
    box_distribution = [0, 0, 0, 0, 0]
    for card in flashcards:
        if 1 <= card.box <= 5:
            box_distribution[card.box - 1] += 1

    recent_quizzes = QuizSession.objects.filter(
        user=request.user, completed_at__isnull=False
    ).order_by("-started_at")[:10]

    quizzes_with_percentages = [
        {"quiz": quiz, "percentage": int(quiz.score / quiz.total * 100) if quiz.total > 0 else 0}
        for quiz in recent_quizzes
    ]

    context: dict[str, Any] = {
        "progress": progress,
        "chart_data": chart_data,
        "box_distribution": box_distribution,
        "recent_quizzes": quizzes_with_percentages,
        "total_words": flashcards.count(),
    }
    return render(request, "progress/dashboard.html", context)


@login_required
def streak_view(request: HttpRequest) -> HttpResponse:
    """Show the user's learning streak calendar."""
    progress, _ = UserProgress.objects.get_or_create(user=request.user)

    today = timezone.now().date()

    streak_data: list[dict[str, Any]] = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        activity = DailyActivity.objects.filter(user=request.user, date=date).first()
        has_activity = activity and (activity.words_reviewed > 0 or activity.quizzes_completed > 0)
        streak_data.append(
            {
                "date": date,
                "day": date.strftime("%d"),
                "month": date.strftime("%b"),
                "active": has_activity,
            }
        )

    context: dict[str, Any] = {
        "progress": progress,
        "streak_data": streak_data,
    }
    return render(request, "progress/streak.html", context)
