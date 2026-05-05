"""Neo4j graph builder for normalized GraphRAG triples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from src.config import Config
from src.entity_normalizer import EntityNormalizer


class GraphBuilder:
    """Build and verify Neo4j graph from extracted triples."""

    ALLOWED_LABELS = {"COMPANY", "PERSON", "PRODUCT", "TECHNOLOGY", "YEAR", "LOCATION"}
    ALLOWED_RELATIONS = {
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

    def __init__(self) -> None:
        """Initialize Neo4j driver."""
        Config.validate()
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
        )

    def close(self) -> None:
        """Close Neo4j driver."""
        self.driver.close()

    def create_constraints(self) -> None:
        """Create unique constraints for supported node labels."""
        with self.driver.session() as session:
            for label in sorted(self.ALLOWED_LABELS):
                try:
                    query = (
                        f"CREATE CONSTRAINT {label}_name IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.name IS UNIQUE"
                    )
                    session.run(query)
                    print(f"✅ Created constraint for {label}")
                except Exception as exc:
                    print(f"⚠️ Error creating constraint for {label}: {exc}")

    def build_graph(self, triples_file: str) -> None:
        """Read triples from JSON and insert normalized graph into Neo4j.

        Args:
            triples_file: Path to triples JSON file.
        """
        triples = self._load_triples(triples_file)
        normalizer = EntityNormalizer.from_triples(triples)
        print(f"🏗️ Bắt đầu xây dựng đồ thị từ {len(triples)} triples...")

        inserted_count = 0
        skipped_count = 0
        with self.driver.session() as session:
            for triple in triples:
                normalized = self._normalize_triple(triple, normalizer)
                if normalized is None:
                    skipped_count += 1
                    continue
                self._merge_triple(session, normalized)
                inserted_count += 1

        print(f"✅ Xây dựng đồ thị hoàn tất: {inserted_count} inserted, {skipped_count} skipped.")

    def verify_graph(self) -> None:
        """Print node and relationship counts."""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            print(f"📊 Thống kê đồ thị: {node_count} Nodes, {rel_count} Relationships.")

    def _load_triples(self, triples_file: str) -> list[dict[str, Any]]:
        """Load triples from JSON file."""
        path = Path(triples_file)
        with path.open(encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        if not isinstance(data, list):
            raise ValueError("Triples file must contain a JSON list.")
        return [item for item in data if isinstance(item, dict)]

    def _normalize_triple(
        self,
        triple: dict[str, Any],
        normalizer: EntityNormalizer,
    ) -> dict[str, str] | None:
        """Normalize and validate one triple."""
        subject_label = str(triple.get("subject_label", "")).upper().strip()
        object_label = str(triple.get("object_label", "")).upper().strip()
        relation = str(triple.get("relation", "")).upper().strip()
        subject = normalizer.canonicalize_name(str(triple.get("subject", "")))
        obj = normalizer.canonicalize_name(str(triple.get("object", "")))

        if (
            subject_label not in self.ALLOWED_LABELS
            or object_label not in self.ALLOWED_LABELS
            or relation not in self.ALLOWED_RELATIONS
            or not subject
            or not obj
        ):
            return None

        linked_subject = normalizer.link_entity(subject, top_k=1)
        linked_object = normalizer.link_entity(obj, top_k=1)
        return {
            "subject": linked_subject[0] if linked_subject else subject,
            "subject_label": subject_label,
            "relation": relation,
            "object": linked_object[0] if linked_object else obj,
            "object_label": object_label,
        }

    def _merge_triple(self, session: Any, triple: dict[str, str]) -> None:
        """MERGE one normalized triple into Neo4j."""
        query = f"""
        MERGE (s:{triple['subject_label']} {{name: $subject}})
        MERGE (o:{triple['object_label']} {{name: $object}})
        MERGE (s)-[r:{triple['relation']}]->(o)
        """
        try:
            session.run(query, subject=triple["subject"], object=triple["object"])
        except Exception as exc:
            print(f"❌ Lỗi khi thực thi Cypher cho triple {triple}: {exc}")


if __name__ == "__main__":
    builder = GraphBuilder()
    builder.create_constraints()
    builder.build_graph("data/triples.json")
    builder.verify_graph()
    builder.close()
