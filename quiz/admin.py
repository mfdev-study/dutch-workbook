from django.contrib import admin

from .models import QuizAnswer, QuizSession


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "quiz_type", "score", "total", "started_at", "completed_at"]
    list_filter = ["quiz_type", "user"]
    date_hierarchy = "started_at"


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ["session", "word", "user_answer", "is_correct", "answered_at"]
    list_filter = ["is_correct"]
