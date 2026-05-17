"""Views for the progress tracking app."""

from datetime import timedelta
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models import Count
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

    # Use aggregation for box distribution — single query
    all_counts = (
        Flashcard.objects.filter(user=request.user).values("box").annotate(count=Count("id"))
    )
    box_distribution = [0, 0, 0, 0, 0]
    total_words = 0
    for entry in all_counts:
        if 1 <= entry["box"] <= 5:
            box_distribution[entry["box"] - 1] = entry["count"]
            total_words += entry["count"]

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
        "total_words": total_words,
    }
    return render(request, "progress/dashboard.html", context)


@login_required
def streak_view(request: HttpRequest) -> HttpResponse:
    """Show the user's learning streak calendar."""
    progress, _ = UserProgress.objects.get_or_create(user=request.user)

    today = timezone.now().date()

    # Single query for all 31 days
    activities = DailyActivity.objects.filter(
        user=request.user,
        date__gte=today - timedelta(days=30),
    )
    activity_map: dict[str, Any] = {}
    for a in activities:
        if a.words_reviewed > 0 or a.quizzes_completed > 0:
            activity_map[a.date] = True

    streak_data: list[dict[str, Any]] = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        streak_data.append(
            {
                "date": date,
                "day": date.strftime("%d"),
                "month": date.strftime("%b"),
                "active": date in activity_map,
            }
        )

    context: dict[str, Any] = {
        "progress": progress,
        "streak_data": streak_data,
    }
    return render(request, "progress/streak.html", context)
