from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class QuizSession(models.Model):
    QUIZ_TYPE_CHOICES = [
        ("MC", "Multiple Choice"),
        ("FL", "Fill-in-the-blank"),
        ("SP", "Speed Round"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz_type = models.CharField(max_length=2, choices=QUIZ_TYPE_CHOICES)
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz_type} ({self.score}/{self.total})"


class QuizAnswer(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE)
    word = models.ForeignKey("words.Word", on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=200)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.session.user.username} - {self.word.dutch} ({'✓' if self.is_correct else '✗'})"
        )
