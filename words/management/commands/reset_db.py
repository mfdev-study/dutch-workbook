from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import CustomUser
from progress.models import DailyActivity, UserProgress
from quiz.models import QuizAnswer, QuizSession
from words.models import Example, Flashcard, Word, WordList


class Command(BaseCommand):
    help = "Reset database to clean state with optional sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-data",
            action="store_true",
            help="Add sample Dutch words after reset",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        if not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "This will DELETE ALL DATA from the database!\n"
                    "Users, words, flashcards, progress - everything will be lost.\n"
                    "This action cannot be undone."
                )
            )

            if input('\nType "YES" to confirm: ') != "YES":
                self.stdout.write("Operation cancelled.")
                return

        self.stdout.write("Starting database reset...")

        # Clear all data in correct order (respecting foreign keys)
        with transaction.atomic():
            self.stdout.write("Clearing examples...")
            Example.objects.all().delete()

            self.stdout.write("Clearing quiz answers...")
            QuizAnswer.objects.all().delete()

            self.stdout.write("Clearing quiz sessions...")
            QuizSession.objects.all().delete()

            self.stdout.write("Clearing flashcards...")
            Flashcard.objects.all().delete()

            self.stdout.write("Clearing word lists...")
            WordList.objects.all().delete()

            self.stdout.write("Clearing words...")
            Word.objects.all().delete()

            self.stdout.write("Clearing progress data...")
            DailyActivity.objects.all().delete()
            UserProgress.objects.all().delete()

            self.stdout.write("Clearing users...")
            CustomUser.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Database cleared successfully!"))

        if options["sample_data"]:
            self.stdout.write("Adding sample data...")
            self._add_sample_data()
            self.stdout.write(self.style.SUCCESS("Sample data added!"))

        self.stdout.write(
            self.style.SUCCESS(
                "\nDatabase reset complete!\nYou can now create a new user account and start fresh."
            )
        )

    def _add_sample_data(self):
        """Add some sample Dutch words for testing"""
        sample_words = [
            # Ukrainian translations
            (
                "goedemorgen",
                "добрий ранок",
                "UK",
                "greeting",
                "Goedemorgen! Hoe gaat het?",
            ),
            ("goedemiddag", "добрий день", "UK", "greeting", "Goedemiddag!"),
            ("goedemorgen", "добрий вечір", "UK", "greeting", "Goedenavond!"),
            ("dank je wel", "дякую", "UK", "politeness", "Dank je wel voor je hulp."),
            (
                "alsjeblieft",
                "будь ласка",
                "UK",
                "politeness",
                "Alsjeblieft, neem een koekje.",
            ),
            ("hoe gaat het", "як справи", "UK", "greeting", "Hoe gaat het met je?"),
            # English translations
            (
                "goedemorgen",
                "good morning",
                "EN",
                "greeting",
                "Goedemorgen! Hoe gaat het?",
            ),
            ("goedemiddag", "good afternoon", "EN", "greeting", "Goedemiddag!"),
            ("goedemorgen", "good evening", "EN", "greeting", "Goedenavond!"),
            (
                "dank je wel",
                "thank you",
                "EN",
                "politeness",
                "Dank je wel voor je hulp.",
            ),
            (
                "alsjeblieft",
                "please",
                "EN",
                "politeness",
                "Alsjeblieft, neem een koekje.",
            ),
            ("hoe gaat het", "how are you", "EN", "greeting", "Hoe gaat het met je?"),
            # Russian translations
            (
                "goedemorgen",
                "доброе утро",
                "RU",
                "greeting",
                "Goedemorgen! Hoe gaat het?",
            ),
            ("goedemiddag", "добрый день", "RU", "greeting", "Goedemiddag!"),
            ("goedemorgen", "добрый вечер", "RU", "greeting", "Goedenavond!"),
            ("dank je wel", "спасибо", "RU", "politeness", "Dank je wel voor je hulp."),
            (
                "alsjeblieft",
                "пожалуйста",
                "RU",
                "politeness",
                "Alsjeblieft, neem een koekje.",
            ),
            ("hoe gaat het", "как дела", "RU", "greeting", "Hoe gaat het met je?"),
        ]

        words_created = 0
        for dutch, translation, source, context, example in sample_words:
            word, created = Word.objects.get_or_create(
                dutch=dutch,
                translation=translation,
                source=source,
                defaults={
                    "context": context,
                    "example": example,
                },
            )
            if created:
                words_created += 1

        self.stdout.write(f"Added {words_created} sample words")
