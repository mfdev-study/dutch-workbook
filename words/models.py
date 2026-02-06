from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, default="#007bff", help_text="Hex color code"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Word(models.Model):
    SOURCE_CHOICES = [
        ("EN", "English-Dutch"),
        ("UK", "Ukrainian-Dutch"),
        ("RU", "Russian-Dutch"),
    ]
    dutch = models.CharField(max_length=200)
    translation = models.CharField(max_length=200)
    source = models.CharField(max_length=2, choices=SOURCE_CHOICES)
    part_of_speech = models.CharField(max_length=50, blank=True, default="")
    context = models.TextField(blank=True, default="")
    example = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["dutch", "translation", "source"]
        ordering = ["dutch"]

    def __str__(self):
        return f"{self.dutch} - {self.translation}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, default="#007bff", help_text="Hex color code"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class CategorizedWord(models.Model):
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="categorized")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="categorized_words"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["word", "category"]
        ordering = ["category__name"]


class Flashcard(models.Model):
    BOX_CHOICES = [(i, i) for i in range(1, 6)]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    box = models.IntegerField(choices=BOX_CHOICES, default=1)
    next_review = models.DateTimeField(null=True, blank=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    ease_factor = models.FloatField(default=2.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "word"]

    def __str__(self):
        return f"{self.user.username} - {self.word.dutch} (Box {self.box})"


class WordList(models.Model):
    LIST_TYPE_CHOICES = [
        ("FAV", "Favorites"),
        ("LEARN", "To Learn"),
        ("MASTERED", "Mastered"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    list_type = models.CharField(max_length=10, choices=LIST_TYPE_CHOICES)
    words = models.ManyToManyField(Word, related_name="lists")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Example(models.Model):
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="examples")
    text = models.TextField(help_text="Example sentence in Dutch")
    translation = models.TextField(
        blank=True, help_text="Translation of the example (optional)"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Example for {self.word.dutch}: {self.text[:50]}..."
