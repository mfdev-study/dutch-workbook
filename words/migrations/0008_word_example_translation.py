"""
Add example_translation field to Word model.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("words", "0007_initial_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="word",
            name="example_translation",
            field=models.TextField(blank=True, default=""),
        ),
    ]
