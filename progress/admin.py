from django.contrib import admin

from .models import DailyActivity, UserProgress


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "words_learned",
        "current_streak",
        "longest_streak",
        "total_quizzes",
        "average_score",
    ]
    search_fields = ["user__username"]


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "words_reviewed", "quizzes_completed", "new_words"]
    list_filter = ["date", "user"]
    date_hierarchy = "date"
