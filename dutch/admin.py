from django.contrib import admin

from .models import DutchArticleQuestion


@admin.register(DutchArticleQuestion)
class DutchArticleQuestionAdmin(admin.ModelAdmin):
    list_display = ["word", "translation", "correct_article", "category", "level", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["level", "category", "correct_article", "is_active"]
    search_fields = ["word", "translation", "explanation"]
    ordering = ["level", "category", "word"]
