import re
import pdfplumber
from django.core.management.base import BaseCommand
from words.models import Word


class Command(BaseCommand):
    help = "Import words from PDF word lists"

    def add_arguments(self, parser):
        parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
        parser.add_argument(
            "--source",
            type=str,
            choices=["EN", "RU"],
            required=True,
            help="Source of the word list (EN=English-Dutch, RU=Russian-Dutch)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )

    def handle(self, *args, **options):
        pdf_path = options["pdf_path"]
        source = options["source"]
        verbose = options.get("verbose", False)

        self.stdout.write(f"Importing words from {pdf_path} (source: {source})")

        words_imported = 0
        words_skipped = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    word_pairs = self.parse_line(line, source)
                    for dutch, translation in word_pairs:
                        word, created = Word.objects.get_or_create(
                            dutch=dutch.strip(),
                            translation=translation.strip(),
                            source=source,
                        )
                        if created:
                            words_imported += 1
                            if verbose:
                                self.stdout.write(f"  Added: {dutch} -> {translation}")
                        else:
                            words_skipped += 1

                self.stdout.write(f"Processed page {page_num}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {words_imported} words")
        )
        if words_skipped > 0:
            self.stdout.write(f"Skipped {words_skipped} duplicate words")

    def parse_line(self, line, source):
        pairs = []

        line = line.strip()
        line = re.sub(r"^Les \d+\s*", "", line)

        if source == "RU":
            pairs = self.parse_russian_line(line)
        else:
            pairs = self.parse_english_line(line)

        return pairs[:5]

    def parse_russian_line(self, line):
        pairs = []

        segments = re.split(r"\s{2,}", line)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            parts = segment.split(" ")

            cyrillic_indices = []
            for i, part in enumerate(parts):
                if self.is_cyrillic(part):
                    cyrillic_indices.append(i)

            if len(cyrillic_indices) >= 1:
                idx = cyrillic_indices[0]
                if idx > 0:
                    dutch = " ".join(parts[:idx])
                    russian = " ".join(parts[idx:])
                    dutch = re.sub(r"\([^)]*\)", "", dutch).strip()
                    if self.is_valid_pair(dutch, russian):
                        pairs.append((dutch, russian))

        return pairs

    def parse_english_line(self, line):
        pairs = []

        segments = re.split(r"\s{2,}", line)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            parts = segment.split(" ")

            if len(parts) >= 2:
                dutch = parts[0]
                english = " ".join(parts[1:])
                dutch = re.sub(r"\([^)]*\)", "", dutch).strip()
                english = re.sub(r"\([^)]*\)", "", english).strip()
                if self.is_valid_pair(dutch, english):
                    pairs.append((dutch, english))

        return pairs

    def is_cyrillic(self, text):
        cyrillic_pattern = re.compile("[а-яА-ЯёЁ]")
        return bool(cyrillic_pattern.search(text))

    def is_valid_pair(self, dutch, translation):
        if not dutch or not translation:
            return False
        if len(dutch) < 2 or len(translation) < 2:
            return False
        if len(dutch) > 60 or len(translation) > 60:
            return False
        if not any(c.isalpha() for c in dutch):
            return False
        if not any(c.isalpha() for c in translation):
            return False
        if dutch.startswith("=") or translation.startswith("="):
            return False
        if " " not in dutch and len(dutch) < 3:
            return False

        return True
