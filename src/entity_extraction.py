"""Triple extraction for GraphRAG knowledge graph construction."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI

from src.config import Config


class EntityExtractor:
    """Extract entities and triples from corpus chunks."""

    def __init__(self) -> None:
        """Initialize Vertex AI chat model and extraction instruction."""
        Config.validate()
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )
        self.system_instruction = """You are a Knowledge Graph extraction expert.
First resolve coreferences inside the text before extracting triples.
Examples: he/she/it/they/the company/ông/công ty này must be replaced by the concrete entity name when the antecedent is clear.

Extract triples in this format:
Subject | Subject_Label | Relation | Object | Object_Label

Allowed node labels: COMPANY, PERSON, PRODUCT, TECHNOLOGY, YEAR, LOCATION.
Allowed relations: FOUNDED_BY, CEO_OF, DEVELOPED, ACQUIRED, INVESTED_IN, PARTNER_WITH, HEADQUARTERED_IN, FOUNDED_IN, USES_TECHNOLOGY, EMPLOYED_BY, CO_FOUNDED.

Rules:
1. Return one triple per line.
2. Use only allowed node labels and relations.
3. Resolve pronouns and descriptive references before writing subject/object.
4. Preserve numeric facts by attaching them to the closest entity when possible.
5. Extract important founder, CEO, acquisition, investment, product, technology, and infrastructure facts.
6. Return triples only. No explanation."""

    def extract_triples(self, text: str) -> list[dict[str, str]]:
        """Extract triples from one text chunk.

        Args:
            text: Source text chunk.

        Returns:
            List of validated triples.
        """
        try:
            prompt_text = f"{self.system_instruction}\n\nText:\n{text}"
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            return self._parse_triples(str(response.content))
        except Exception as exc:
            print(f"❌ Lỗi trích xuất: {exc}")
            return []

    def process_corpus(self, input_file: str, output_file: str) -> None:
        """Process full corpus and save extracted triples.

        Args:
            input_file: Source corpus path.
            output_file: Output triples JSON path.
        """
        if not os.path.exists(input_file):
            print(f"❌ Không tìm thấy file corpus: {input_file}")
            return

        with open(input_file, encoding="utf-8") as file_obj:
            content = file_obj.read()

        articles = content.split("=" * 50)
        valid_articles = [article.strip() for article in articles if len(article.strip()) > 100]
        all_triples: list[dict[str, str]] = []

        print(f"🔄 Bắt đầu trích xuất từ {len(valid_articles)} bài viết...")
        for index, article in enumerate(valid_articles):
            print(f"📝 Đang xử lý bài {index + 1}/{len(valid_articles)}...")
            triples = self.extract_triples(article[:3000])
            all_triples.extend(triples)

        unique_triples = self._deduplicate_triples(all_triples)
        with open(output_file, "w", encoding="utf-8") as file_obj:
            json.dump(unique_triples, file_obj, indent=4, ensure_ascii=False)

        print(f"✅ Đã trích xuất xong {len(unique_triples)} triples. Lưu tại: {output_file}")

    def _parse_triples(self, content: str) -> list[dict[str, str]]:
        """Parse LLM text response into triples."""
        triples: list[dict[str, str]] = []
        for line in content.strip().split("\n"):
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 5:
                continue
            triple = {
                "subject": parts[0],
                "subject_label": parts[1].upper(),
                "relation": parts[2].upper(),
                "object": parts[3],
                "object_label": parts[4].upper(),
            }
            if self._is_valid_triple(triple):
                triples.append(triple)
        return triples

    def _is_valid_triple(self, triple: dict[str, str]) -> bool:
        """Validate labels, relation, and non-empty entity names."""
        labels = {"COMPANY", "PERSON", "PRODUCT", "TECHNOLOGY", "YEAR", "LOCATION"}
        relations = {
            "FOUNDED_BY",
            "CEO_OF",
            "DEVELOPED",
            "ACQUIRED",
            "INVESTED_IN",
            "PARTNER_WITH",
            "HEADQUARTERED_IN",
            "FOUNDED_IN",
            "USES_TECHNOLOGY",
            "EMPLOYED_BY",
            "CO_FOUNDED",
        }
        return bool(
            triple["subject"]
            and triple["object"]
            and triple["subject_label"] in labels
            and triple["object_label"] in labels
            and triple["relation"] in relations
        )

    def _deduplicate_triples(self, triples: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Deduplicate triples by normalized subject, relation, and object."""
        unique_triples: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for triple in triples:
            key = (
                str(triple["subject"]).lower(),
                str(triple["relation"]).upper(),
                str(triple["object"]).lower(),
            )
            if key not in seen:
                seen.add(key)
                unique_triples.append({key_: str(value) for key_, value in triple.items()})
        return unique_triples


if __name__ == "__main__":
    extractor = EntityExtractor()
    extractor.process_corpus("data/tech_company_corpus.txt", "data/triples.json")
