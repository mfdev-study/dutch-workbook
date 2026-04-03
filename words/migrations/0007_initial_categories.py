"""
Initial categories data migration.
"""

from django.db import migrations


def create_categories(apps, schema_editor):
    Category = apps.get_model("words", "Category")

    categories = [
        {"name": "Greetings", "description": "Common Dutch greetings and farewells"},
        {"name": "Numbers", "description": "Numbers and counting in Dutch"},
        {"name": "Family", "description": "Family members and relationships"},
        {"name": "Food", "description": "Food and drinks vocabulary"},
        {"name": "Animals", "description": "Common animals in Dutch"},
        {"name": "Colors", "description": "Colors in Dutch"},
        {"name": "Time", "description": "Time-related words"},
        {"name": "Weather", "description": "Weather expressions"},
        {"name": "Travel", "description": "Travel and transportation"},
        {"name": "Shopping", "description": "Shopping vocabulary"},
        {"name": "Work", "description": "Work and professions"},
        {"name": "Education", "description": "School and education"},
        {"name": "Health", "description": "Health and body parts"},
        {"name": "Emotions", "description": "Emotions and feelings"},
        {"name": "House", "description": "House and furniture"},
        {"name": "Nature", "description": "Nature and outdoors"},
        {"name": "Clothing", "description": "Clothing and accessories"},
        {"name": "Sports", "description": "Sports and hobbies"},
        {"name": "Entertainment", "description": "Movies, music, and entertainment"},
        {"name": "Technology", "description": "Technology and devices"},
        {"name": "City", "description": "City and places"},
        {"name": "Country", "description": "Countries and nationalities"},
        {"name": "Days of Week", "description": "Days of the week"},
        {"name": "Months", "description": "Months of the year"},
        {"name": "Verbs", "description": "Common Dutch verbs"},
        {"name": "Adjectives", "description": "Common adjectives"},
        {"name": "Phrases", "description": "Useful phrases and expressions"},
        {"name": "Idioms", "description": "Dutch idioms and expressions"},
        {"name": "Grammar", "description": "Grammar-related vocabulary"},
        {"name": "Questions", "description": "Question words"},
    ]

    for cat in categories:
        Category.objects.get_or_create(
            name=cat["name"], defaults={"description": cat["description"]}
        )


def remove_categories(apps, schema_editor):
    Category = apps.get_model("words", "Category")
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("words", "0006_alter_word_source"),
    ]

    operations = [
        migrations.RunPython(create_categories, remove_categories),
    ]
