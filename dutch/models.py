from django.core.exceptions import ValidationError
from django.db import models


class DutchArticleQuestion(models.Model):
    LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
    ]

    CATEGORY_CHOICES = [
        ("plural", "Plural"),
        ("person", "Person"),
        ("diminutive", "Diminutive -je"),
        ("ing", "-ing"),
        ("heid", "-heid"),
        ("memorize", "Memorize"),
    ]

    ARTICLE_CHOICES = [
        ("de", "de"),
        ("het", "het"),
    ]

    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=150, blank=True)
    correct_article = models.CharField(max_length=3, choices=ARTICLE_CHOICES)
    explanation = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, default="A1")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.correct_article} {self.word}"

    def clean(self):
        super().clean()
        errors = {}
        if not self.word or not self.word.strip():
            errors["word"] = "Word cannot be empty."
        if self.correct_article not in dict(self.ARTICLE_CHOICES):
            errors["correct_article"] = "Article must be 'de' or 'het'."
        if self.category not in dict(self.CATEGORY_CHOICES):
            errors["category"] = "Category must be valid."
        if self.level not in dict(self.LEVEL_CHOICES):
            errors["level"] = "Level must be A1 or A2."
        if errors:
            raise ValidationError(errors)
