"""Hybrid corpus evidence retriever for GraphRAG.

The retriever provides a generic text-evidence fallback for facts that are
awkward to represent as triples, such as numeric stakes, dates, and long
corporate restructuring statements.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


class HybridEvidenceRetriever:
    """Retrieve source sentences using lightweight BM25-like scoring."""

    def __init__(self, corpus_path: str = "data/tech_company_corpus.txt") -> None:
        """Initialize retriever.

        Args:
            corpus_path: Path to source corpus.
        """
        self.corpus_path = Path(corpus_path)
        self.sentences = self._load_sentences()
        self.document_frequencies = self._build_document_frequencies()
        self.avg_sentence_len = self._average_sentence_length()

    def retrieve(
        self,
        question: str,
        entities: Iterable[str],
        relation_terms: Iterable[str],
        top_k: int = 6,
    ) -> list[str]:
        """Retrieve ranked source evidence snippets.

        Args:
            question: User question.
            entities: Linked entity names.
            relation_terms: Relation-intent keywords.
            top_k: Number of snippets to return.

        Returns:
            Evidence lines prefixed with SOURCE_EVIDENCE.
        """
        if not self.sentences:
            return []

        query_terms = self._tokenize(question)
        for entity in entities:
            query_terms.extend(self._tokenize(entity))
        for term in relation_terms:
            query_terms.extend(self._tokenize(term))

        query_counter = Counter(term for term in query_terms if len(term) > 2)
        if not query_counter:
            return []

        scored: list[tuple[float, str]] = []
        for sentence in self.sentences:
            score = self._score_sentence(sentence, query_counter)
            if score > 0:
                scored.append((score, sentence))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [f"SOURCE_EVIDENCE: {sentence}" for _, sentence in scored[:top_k]]

    def _load_sentences(self) -> list[str]:
        """Load and split corpus into sentences."""
        if not self.corpus_path.exists():
            return []
        text = self.corpus_path.read_text(encoding="utf-8")
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        return [sentence.strip() for sentence in raw_sentences if len(sentence.strip()) > 20]

    def _build_document_frequencies(self) -> Counter[str]:
        """Build sentence-level document frequencies."""
        frequencies: Counter[str] = Counter()
        for sentence in self.sentences:
            frequencies.update(set(self._tokenize(sentence)))
        return frequencies

    def _average_sentence_length(self) -> float:
        """Return average sentence length in tokens."""
        if not self.sentences:
            return 1.0
        total = sum(len(self._tokenize(sentence)) for sentence in self.sentences)
        return max(total / len(self.sentences), 1.0)

    def _score_sentence(self, sentence: str, query_counter: Counter[str]) -> float:
        """Score one sentence using BM25-like formula plus phrase bonus."""
        tokens = self._tokenize(sentence)
        if not tokens:
            return 0.0

        token_counts = Counter(tokens)
        sentence_len = len(tokens)
        total_docs = max(len(self.sentences), 1)
        k1 = 1.5
        b = 0.75
        score = 0.0

        for term, query_weight in query_counter.items():
            frequency = token_counts.get(term, 0)
            if frequency == 0:
                continue
            doc_frequency = self.document_frequencies.get(term, 0)
            idf = math.log(1 + (total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5))
            denominator = frequency + k1 * (1 - b + b * sentence_len / self.avg_sentence_len)
            score += query_weight * idf * (frequency * (k1 + 1) / denominator)

        sentence_lower = sentence.lower()
        for phrase in self._important_phrases(query_counter):
            if phrase in sentence_lower:
                score += 2.0
        return score

    def _important_phrases(self, query_counter: Counter[str]) -> list[str]:
        """Return generic high-value phrases for evidence matching."""
        terms = set(query_counter.keys())
        phrases: list[str] = []
        if {"cloud", "platform"} & terms:
            phrases.extend(["microsoft azure", "azure based", "cloud platform"])
        if {"stake", "owned", "holds", "hold"} & terms:
            phrases.extend(["% stake", "holds a", "owned a"])
        if {"ceo", "chief", "executive"} & terms:
            phrases.extend(["chief executive officer", "became the ceo", "appointed ceo"])
        if {"replacing", "replaced", "transitioned"} & terms:
            phrases.extend(["replacing", "replaced", "transitioned"])
        return phrases

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase alphanumeric terms."""
        return re.findall(r"[a-z0-9%]+", text.lower())
