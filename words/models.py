from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Word(models.Model):
    """Dutch vocabulary word model."""

    class Source(models.TextChoices):
        ENGLISH = "EN", "English-Dutch"
        RUSSIAN = "RU", "Russian-Dutch"
        UKRAINIAN = "UK", "Ukrainian-Dutch"

    dutch = models.CharField(max_length=200, db_index=True)
    translation = models.CharField(max_length=200, db_index=True)
    source = models.CharField(
        max_length=2, choices=Source.choices, default=Source.ENGLISH, db_index=True
    )
    part_of_speech = models.CharField(max_length=50, blank=True, default="")
    context = models.TextField(blank=True, default="")
    example = models.TextField(blank=True, default="")
    example_translation = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dutch"]
        constraints = [
            models.UniqueConstraint(
                fields=["dutch", "translation", "source"],
                name="unique_word_translation_source",
            ),
        ]

    def __str__(self):
        return f"{self.dutch} - {self.translation}"

    def related_words(self, relation_type=None):
        """Get related words, optionally filtered by relation type."""
        qs_out = self.relations_out.select_related("word_to")
        qs_in = self.relations_in.select_related("word_from")
        if relation_type:
            qs_out = qs_out.filter(relation_type=relation_type)
            qs_in = qs_in.filter(relation_type=relation_type)
        related = []
        for r in qs_out:
            related.append(
                {"word": r.word_to, "type": r.relation_type, "label": r.get_relation_type_display()}
            )
        for r in qs_in:
            related.append(
                {
                    "word": r.word_from,
                    "type": r.relation_type,
                    "label": r.get_relation_type_display(),
                }
            )
        return related


class Flashcard(models.Model):
    """User flashcard for word learning with spaced repetition."""

    class Box(models.IntegerChoices):
        BOX_1 = 1
        BOX_2 = 2
        BOX_3 = 3
        BOX_4 = 4
        BOX_5 = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    box = models.IntegerField(choices=Box.choices, default=Box.BOX_1)
    next_review = models.DateTimeField(null=True, blank=True, db_index=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    ease_factor = models.FloatField(default=2.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "next_review"], name="idx_user_next_review"),
            models.Index(fields=["user", "box"], name="idx_user_box"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "word"],
                name="unique_user_word_flashcard",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.word.dutch} (Box {self.box})"


class WordList(models.Model):
    """User's word list for organization."""

    class ListType(models.TextChoices):
        FAVORITES = "FAV", "Favorites"
        TO_LEARN = "LEARN", "To Learn"
        MASTERED = "MASTERED", "Mastered"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    list_type = models.CharField(max_length=10, choices=ListType.choices)
    words = models.ManyToManyField(Word, related_name="lists")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_list_name",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class WordRelation(models.Model):
    """Semantic relationship between two Dutch words."""

    class RelationType(models.TextChoices):
        SYNONYM = "SYN", "Synonym"
        ANTONYM = "ANT", "Antonym"
        HYPERNYM = "HYP", "Hypernym"
        HYPONYM = "HPO", "Hyponym"
        MERONYM = "MER", "Meronym"
        HOLONYM = "HOL", "Holonym"
        RELATED = "REL", "Related"
        DERIVED = "DER", "Derived"

    word_from = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="relations_out",
    )
    word_to = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="relations_in",
    )
    relation_type = models.CharField(
        max_length=3,
        choices=RelationType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["word_from", "relation_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["word_from", "word_to", "relation_type"],
                name="unique_word_relation",
            ),
        ]

    def __str__(self):
        return (
            f"{self.word_from.dutch} → [{self.get_relation_type_display()}] → {self.word_to.dutch}"
        )


class Example(models.Model):
    """User-added example sentence for a word."""

    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="examples",
    )
    text = models.TextField(help_text="Example sentence in Dutch")
    translation = models.TextField(
        blank=True,
        help_text="Translation of the example (optional)",
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["word", "text"],
                name="unique_word_example",
            ),
        ]

    def __str__(self):
        return f"Example for {self.word.dutch}: {self.text[:50]}..."
