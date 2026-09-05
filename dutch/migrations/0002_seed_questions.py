"""Seed the initial de/het article questions.

Idempotent: only inserts questions whose (word, correct_article) pair does not
already exist, so admin edits are never overwritten on re-run.
"""

from django.db import migrations

SEED_QUESTIONS = [
    {"word": "kinderen", "correct_article": "de", "category": "plural", "translation": "children", "explanation": "Kinderen is a plural noun, so it always uses de."},
    {"word": "vriend", "correct_article": "de", "category": "person", "translation": "friend", "explanation": "People and professions normally take de."},
    {"word": "huisje", "correct_article": "het", "category": "diminutive", "translation": "little house", "explanation": "Diminutives ending in -je take het."},
    {"word": "regering", "correct_article": "de", "category": "ing", "translation": "government", "explanation": "Nouns ending in -ing take de."},
    {"word": "gezondheid", "correct_article": "de", "category": "heid", "translation": "health", "explanation": "Nouns ending in -heid take de."},
    {"word": "tafel", "correct_article": "de", "category": "memorize", "translation": "table", "explanation": "You'll need to memorize this one: tafel uses de."},
    {"word": "huis", "correct_article": "het", "category": "memorize", "translation": "house", "explanation": "Memorize this one: huis uses het."},
    {"word": "meisje", "correct_article": "het", "category": "diminutive", "translation": "girl", "explanation": "Diminutives ending in -je take het."},
    {"word": "boeken", "correct_article": "de", "category": "plural", "translation": "books", "explanation": "Boeken is a plural noun, so it always uses de."},
    {"word": "dokter", "correct_article": "de", "category": "person", "translation": "doctor", "explanation": "People and professions normally take de."},
    {"word": "betaling", "correct_article": "de", "category": "ing", "translation": "payment", "explanation": "Nouns ending in -ing take de."},
    {"word": "vrijheid", "correct_article": "de", "category": "heid", "translation": "freedom", "explanation": "Nouns ending in -heid take de."},
    {"word": "hondje", "correct_article": "het", "category": "diminutive", "translation": "little dog", "explanation": "Diminutives ending in -je take het."},
    {"word": "auto", "correct_article": "de", "category": "memorize", "translation": "car", "explanation": "Memorize this one: auto uses de."},
    {"word": "boek", "correct_article": "het", "category": "memorize", "translation": "book", "explanation": "Memorize this one: boek uses het."},
]


def seed_questions(apps, schema_editor):
    question_model = apps.get_model("dutch", "DutchArticleQuestion")
    existing = set(question_model.objects.values_list("word", "correct_article"))
    to_create = [
        question_model(**q)
        for q in SEED_QUESTIONS
        if (q["word"], q["correct_article"]) not in existing
    ]
    question_model.objects.bulk_create(to_create)


def unseed_questions(apps, schema_editor):
    question_model = apps.get_model("dutch", "DutchArticleQuestion")
    words = [q["word"] for q in SEED_QUESTIONS]
    question_model.objects.filter(word__in=words).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("dutch", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_questions, unseed_questions),
    ]
