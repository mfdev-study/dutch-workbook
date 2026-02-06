from django.db import models
from django.contrib.auth import get_user_model

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


class DailyActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    words_reviewed = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    new_words = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_answers = models.IntegerField(default=0)

    class Meta:
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.username} - {self.date}"
