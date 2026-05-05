"""Entity normalization and lightweight entity linking for GraphRAG.

This module avoids benchmark-specific query tricks by building generic aliases
from graph/corpus entity names and resolving question entities via exact,
normalized, abbreviation, substring, and fuzzy matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from typing import Iterable


LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "plc",
}


QUESTION_STOPWORDS = {
    "what",
    "who",
    "when",
    "where",
    "which",
    "why",
    "how",
    "company",
    "companies",
    "parent",
    "ceo",
    "chief",
    "executive",
    "officer",
    "cloud",
    "platform",
    "infrastructure",
    "stake",
    "percentage",
    "restructuring",
    "after",
    "before",
    "released",
    "created",
    "owns",
    "owned",
    "models",
    "ring",
}


@dataclass
class EntityNormalizer:
    """Normalize and link entity aliases to canonical graph node names.

    Attributes:
        canonical_names: Known graph or corpus entity names.
        alias_to_canonical: Mapping from normalized alias to canonical entity.
    """

    canonical_names: list[str]
    alias_to_canonical: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        """Build alias index after initialization."""
        self.canonical_names = list(dict.fromkeys(self.canonical_names))
        self.alias_to_canonical = self._build_alias_index(self.canonical_names)

    @classmethod
    def from_triples(cls, triples: Iterable[dict[str, str]]) -> "EntityNormalizer":
        """Create normalizer from triples.

        Args:
            triples: Iterable of triples containing subject/object fields.

        Returns:
            EntityNormalizer initialized with subject and object names.
        """
        names: list[str] = []
        for triple in triples:
            subject = triple.get("subject", "").strip()
            obj = triple.get("object", "").strip()
            if subject:
                names.append(subject)
            if obj:
                names.append(obj)
        return cls(names)

    def normalize_text(self, value: str) -> str:
        """Normalize text for entity matching.

        Args:
            value: Raw text.

        Returns:
            Lowercase punctuation-normalized text.
        """
        text = value.lower().strip()
        text = re.sub(r"&", " and ", text)
        text = re.sub(r"[^a-z0-9%]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def canonicalize_name(self, value: str) -> str:
        """Clean entity names before graph insertion.

        Args:
            value: Raw entity name.

        Returns:
            Canonical display name.
        """
        text = re.sub(r"\s+", " ", value).strip()
        return text.strip('"\'`.,;:')

    def link_entities(self, entities: Iterable[str], top_k: int = 3) -> list[str]:
        """Link raw entity mentions to canonical known names.

        Args:
            entities: Raw entity mentions.
            top_k: Maximum canonical names returned per mention.

        Returns:
            Deduplicated canonical entity names and original mentions.
        """
        linked: list[str] = []
        for entity in entities:
            entity = self.canonicalize_name(entity)
            if not entity:
                continue
            matches = self.link_entity(entity, top_k=top_k)
            linked.extend(matches or [entity])
        return list(dict.fromkeys(linked))

    def link_entity(self, entity: str, top_k: int = 3) -> list[str]:
        """Link one entity mention to canonical known names.

        Args:
            entity: Raw entity mention.
            top_k: Maximum returned matches.

        Returns:
            Candidate canonical names ordered by confidence.
        """
        normalized = self.normalize_text(entity)
        if not normalized or normalized in QUESTION_STOPWORDS:
            return []

        if normalized in self.alias_to_canonical:
            return [self.alias_to_canonical[normalized]]

        substring_matches = self._substring_matches(normalized)
        if substring_matches:
            return substring_matches[:top_k]

        aliases = list(self.alias_to_canonical.keys())
        close_aliases = get_close_matches(normalized, aliases, n=top_k, cutoff=0.78)
        return list(dict.fromkeys(self.alias_to_canonical[item] for item in close_aliases))

    def _substring_matches(self, normalized: str) -> list[str]:
        """Find canonical names containing or contained by normalized mention."""
        matches: list[tuple[float, str]] = []
        if len(normalized) < 4 or normalized in QUESTION_STOPWORDS:
            return []
        for alias, canonical in self.alias_to_canonical.items():
            if len(alias) < 4 or alias in QUESTION_STOPWORDS:
                continue
            if normalized in alias or alias in normalized:
                ratio = SequenceMatcher(None, normalized, alias).ratio()
                if ratio < 0.72:
                    continue
                matches.append((ratio, canonical))
        matches.sort(key=lambda item: item[0], reverse=True)
        return list(dict.fromkeys(canonical for _, canonical in matches))

    def _build_alias_index(self, names: Iterable[str]) -> dict[str, str]:
        """Build normalized alias mapping from canonical names."""
        alias_to_canonical: dict[str, str] = {}
        for name in names:
            canonical = self.canonicalize_name(name)
            for alias in self._generate_aliases(canonical):
                normalized = self.normalize_text(alias)
                if normalized:
                    alias_to_canonical.setdefault(normalized, canonical)
        return alias_to_canonical

    def _generate_aliases(self, name: str) -> set[str]:
        """Generate generic aliases from one canonical name."""
        aliases = {name}
        normalized = self.normalize_text(name)
        if normalized:
            aliases.add(normalized)

        without_parentheses = re.sub(r"\([^)]*\)", "", name).strip()
        if without_parentheses:
            aliases.add(without_parentheses)

        parenthetical_values = re.findall(r"\(([^)]+)\)", name)
        aliases.update(value.strip() for value in parenthetical_values if value.strip())

        tokens = normalized.split()
        if len(tokens) > 1 and tokens[-1] in LEGAL_SUFFIXES:
            aliases.add(" ".join(tokens[:-1]))

        initials = "".join(token[0] for token in tokens if token and token not in LEGAL_SUFFIXES)
        if len(initials) >= 2:
            aliases.add(initials)

        acronym_words = re.findall(r"\b[A-Z]{2,}\b", name)
        aliases.update(acronym_words)
        return aliases
