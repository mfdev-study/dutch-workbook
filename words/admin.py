from django.contrib import admin

from .models import Example, Flashcard, Word, WordList


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ["dutch", "translation", "source", "part_of_speech", "created_at"]
    list_filter = ["source", "part_of_speech"]
    search_fields = ["dutch", "translation"]
    date_hierarchy = "created_at"


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ["user", "word", "box", "next_review", "last_reviewed"]
    list_filter = ["box", "user"]
    search_fields = ["user__username", "word__dutch"]


@admin.register(WordList)
class WordListAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "list_type", "created_at"]
    list_filter = ["list_type"]


@admin.register(Example)
class ExampleAdmin(admin.ModelAdmin):
    list_display = ["word", "created_by", "created_at"]
    search_fields = ["word__dutch", "text"]
