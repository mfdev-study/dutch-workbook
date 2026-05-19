"""
AI-powered semantic relation generation service.
Identifies lexical relationships between existing Dutch words.
"""

import json
import logging
import re
from dataclasses import dataclass

from words.models import Word, WordRelation

logger = logging.getLogger(__name__)

RELATION_TYPES = {
    "SYNONYM": WordRelation.RelationType.SYNONYM,
    "ANTONYM": WordRelation.RelationType.ANTONYM,
    "HYPERNYM": WordRelation.RelationType.HYPERNYM,
    "HYPONYM": WordRelation.RelationType.HYPONYM,
    "MERONYM": WordRelation.RelationType.MERONYM,
    "HOLONYM": WordRelation.RelationType.HOLONYM,
    "RELATED": WordRelation.RelationType.RELATED,
    "DERIVED": WordRelation.RelationType.DERIVED,
}


@dataclass
class RelationEntry:
    word_a: str
    word_b: str
    relation_type: str


class RelationGenerationService:
    def __init__(self):
        from nederlandse_workbook.utils.opencode import OpenCodeClient

        self.client = OpenCodeClient()

    def generate_relations(self, batch_size: int = 50) -> int:
        """Generate relations for all words in the database."""
        all_words = list(Word.objects.values_list("dutch", "id"))
        total_relations = 0

        for i in range(0, len(all_words), batch_size):
            batch = all_words[i : i + batch_size]
            word_list = [{"dutch": w[0], "id": w[1]} for w in batch]
            word_texts = [w["dutch"] for w in word_list]
            dutch_to_id = {w["dutch"]: w["id"] for w in word_list}

            prompt = self._build_prompt(word_texts)
            _, response = self.client.chat(prompt)

            if not response:
                logger.warning("Empty response for batch starting at index %d", i)
                continue

            relations = self._parse_response(response)
            saved = self._save_relations(relations, dutch_to_id)
            total_relations += saved
            logger.info(
                "Batch %d-%d: found %d relations, saved %d",
                i,
                i + len(batch) - 1,
                len(relations),
                saved,
            )

        return total_relations

    def _build_prompt(self, words: list[str]) -> str:
        word_list_str = "\n".join(f"- {w}" for w in words)
        return f"""You are a Dutch linguistics expert. Below is a list of Dutch words.
Identify semantic relationships BETWEEN these words.

{word_list_str}

Return ONLY a JSON array of relations with this exact structure:
[
  {{
    "word_a": "first_dutch_word",
    "word_b": "second_dutch_word",
    "relation": "SYNONYM"
  }}
]

Valid relation types:
- SYNONYM: words with similar meaning
- ANTONYM: words with opposite meaning
- HYPERNYM: word_a is a broader category of word_b (e.g., "voertuig" → "auto")
- HYPONYM: word_a is a specific instance of word_b (e.g., "auto" → "voertuig")
- MERONYM: word_a is a part of word_b (e.g., "wiel" → "auto")
- HOLONYM: word_a contains word_b (e.g., "auto" → "wiel")
- RELATED: words that are semantically associated (same topic/domain)
- DERIVED: words sharing the same root (e.g., "lopen" → "gelopen")

Rules:
- Only return relations between words from the provided list
- Include BOTH directions for hierarchical relations (e.g., HYPERNYM + HYPONYM)
- For SYNONYM and ANTONYM, only include one direction
- Be conservative — only include REAL semantic relations, not loose associations
- Return exactly the Dutch text as it appears in the list, with correct articles

Return ONLY the JSON array, no other text."""

    def _parse_response(self, response: str) -> list[RelationEntry]:
        """Parse JSON response from AI."""
        cleaned = self._clean_response(response)

        json_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return [
                        RelationEntry(
                            word_a=item["word_a"],
                            word_b=item["word_b"],
                            relation_type=item["relation"],
                        )
                        for item in data
                        if all(k in item for k in ("word_a", "word_b", "relation"))
                    ]
            except (json.JSONDecodeError, KeyError):
                pass

        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [
                    RelationEntry(
                        word_a=item["word_a"],
                        word_b=item["word_b"],
                        relation_type=item["relation"],
                    )
                    for item in data
                    if all(k in item for k in ("word_a", "word_b", "relation"))
                ]
        except (json.JSONDecodeError, KeyError):
            pass

        return []

    def _clean_response(self, response: str) -> str:
        """Strip ANSI codes, tool log lines, and markdown fences from AI output."""
        from nederlandse_workbook.utils.opencode import _strip_ansi

        cleaned = _strip_ansi(response)
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith((">", "→"))
        )
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = re.sub(r"^[^[]*", "", cleaned.strip())
        return cleaned

    def _save_relations(self, relations: list[RelationEntry], dutch_to_id: dict[str, int]) -> int:
        """Save parsed relations to database, creating inverse where needed."""
        saved_count = 0

        for rel in relations:
            word_a_dutch = rel.word_a.strip().lower()
            word_b_dutch = rel.word_b.strip().lower()
            rel_type = rel.relation_type.upper()

            if rel_type not in RELATION_TYPES:
                logger.debug("Unknown relation type: %s", rel_type)
                continue

            word_a_id = self._find_word(word_a_dutch, dutch_to_id)
            word_b_id = self._find_word(word_b_dutch, dutch_to_id)

            if not word_a_id or not word_b_id:
                continue
            if word_a_id == word_b_id:
                continue

            rel_enum = RELATION_TYPES[rel_type]

            _, created = WordRelation.objects.get_or_create(
                word_from_id=word_a_id,
                word_to_id=word_b_id,
                relation_type=rel_enum,
            )
            if created:
                saved_count += 1

            if rel_type in ("SYNONYM", "ANTONYM", "RELATED", "DERIVED"):
                _, created_inv = WordRelation.objects.get_or_create(
                    word_from_id=word_b_id,
                    word_to_id=word_a_id,
                    relation_type=rel_enum,
                )
                if created_inv:
                    saved_count += 1

            elif rel_type == "HYPERNYM":
                _, created_inv = WordRelation.objects.get_or_create(
                    word_from_id=word_b_id,
                    word_to_id=word_a_id,
                    relation_type=WordRelation.RelationType.HYPONYM,
                )
                if created_inv:
                    saved_count += 1

            elif rel_type == "HYPONYM":
                _, created_inv = WordRelation.objects.get_or_create(
                    word_from_id=word_b_id,
                    word_to_id=word_a_id,
                    relation_type=WordRelation.RelationType.HYPERNYM,
                )
                if created_inv:
                    saved_count += 1

            elif rel_type == "MERONYM":
                _, created_inv = WordRelation.objects.get_or_create(
                    word_from_id=word_b_id,
                    word_to_id=word_a_id,
                    relation_type=WordRelation.RelationType.HOLONYM,
                )
                if created_inv:
                    saved_count += 1

            elif rel_type == "HOLONYM":
                _, created_inv = WordRelation.objects.get_or_create(
                    word_from_id=word_b_id,
                    word_to_id=word_a_id,
                    relation_type=WordRelation.RelationType.MERONYM,
                )
                if created_inv:
                    saved_count += 1

        return saved_count

    def _find_word(self, dutch: str, dutch_to_id: dict[str, int]) -> int | None:
        """Find a word ID from the dict, with fallback DB lookup."""
        if dutch in dutch_to_id:
            return dutch_to_id[dutch]

        try:
            word = Word.objects.filter(dutch__iexact=dutch).values("id").first()
            if word:
                return word["id"]
        except Word.DoesNotExist:
            pass

        return None
