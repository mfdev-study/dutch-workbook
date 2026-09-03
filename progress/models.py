from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class UserProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    words_learned = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity = models.DateField(null=True, blank=True)
    total_quizzes = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.words_learned} words"


def update_streak(user) -> None:
    """Recalculate current_streak, longest_streak, and last_activity from DailyActivity."""
    progress, _ = UserProgress.objects.get_or_create(user=user)
    today = timezone.now().date()

    active_dates = set(
        DailyActivity.objects.filter(
            user=user,
            date__lte=today,
        )
        .exclude(words_reviewed=0, quizzes_completed=0, new_words=0)
        .values_list("date", flat=True)
    )

    if not active_dates:
        progress.current_streak = 0
        progress.last_activity = None
        progress.save(update_fields=["current_streak", "longest_streak", "last_activity"])
        return

    progress.last_activity = max(active_dates)

    # Count consecutive active days ending today (or yesterday if today is inactive)
    streak = 0
    date = today
    while date in active_dates:
        streak += 1
        date -= timedelta(days=1)
    progress.current_streak = streak

    if streak > progress.longest_streak:
        progress.longest_streak = streak

    progress.save(update_fields=["current_streak", "longest_streak", "last_activity"])


class DailyActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    words_reviewed = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    new_words = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_answers = models.IntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.username} - {self.date}"
