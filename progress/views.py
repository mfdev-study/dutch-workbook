from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from quiz.models import QuizSession
from words.models import Flashcard

from .models import DailyActivity, UserProgress


@login_required
def progress_dashboard(request):
    progress, created = UserProgress.objects.get_or_create(user=request.user)

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    daily_activities = DailyActivity.objects.filter(user=request.user, date__gte=week_ago).order_by(
        "date"
    )

    activity_data = {a.date: a for a in daily_activities}

    chart_data = []
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
    box_distribution = [0, 0, 0, 0, 0]
    for card in flashcards:
        if 1 <= card.box <= 5:
            box_distribution[card.box - 1] += 1

    recent_quizzes = QuizSession.objects.filter(
        user=request.user, completed_at__isnull=False
    ).order_by("-started_at")[:10]

    # Calculate quiz percentages for template
    quizzes_with_percentages = []
    for quiz in recent_quizzes:
        if quiz.total > 0:
            percentage = int((quiz.score / quiz.total) * 100)
        else:
            percentage = 0
        quizzes_with_percentages.append({"quiz": quiz, "percentage": percentage})

    context = {
        "progress": progress,
        "chart_data": chart_data,
        "box_distribution": box_distribution,
        "recent_quizzes": quizzes_with_percentages,
        "total_words": flashcards.count(),
    }
    return render(request, "progress/dashboard.html", context)


@login_required
def streak_view(request):
    progress = UserProgress.objects.get(user=request.user)

    today = timezone.now().date()

    streak_data = []
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

    context = {
        "progress": progress,
        "streak_data": streak_data,
    }
    return render(request, "progress/streak.html", context)
