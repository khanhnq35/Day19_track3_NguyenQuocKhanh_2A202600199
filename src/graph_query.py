"""GraphRAG query engine with generic entity linking and hybrid retrieval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI
from neo4j import GraphDatabase

from src.config import Config
from src.entity_normalizer import EntityNormalizer, QUESTION_STOPWORDS
from src.hybrid_retriever import HybridEvidenceRetriever


class GraphQueryEngine:
    """GraphRAG query engine optimized for scalable multi-hop reasoning."""

    def __init__(self, corpus_path: str = "data/tech_company_corpus.txt") -> None:
        """Initialize Neo4j, LLM, entity linker, and text retriever.

        Args:
            corpus_path: Path to source corpus for evidence retrieval.
        """
        Config.validate()
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
        )
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )
        self.hybrid_retriever = HybridEvidenceRetriever(corpus_path=corpus_path)
        node_names = self._load_graph_node_names()
        if not node_names:
            node_names = self._load_triple_node_names()
        self.entity_normalizer = EntityNormalizer(node_names)

    def close(self) -> None:
        """Close Neo4j driver."""
        self.driver.close()

    def extract_entities(self, question: str) -> list[str]:
        """Extract and link question entities to graph canonical names.

        Args:
            question: User question.

        Returns:
            Linked canonical entity names plus unresolved high-signal mentions.
        """
        raw_entities = self._extract_raw_entities(question)
        filtered_entities = [
            entity
            for entity in raw_entities
            if self.entity_normalizer.normalize_text(entity) not in QUESTION_STOPWORDS
        ]
        linked_entities = self.entity_normalizer.link_entities(filtered_entities, top_k=3)
        return list(dict.fromkeys(linked_entities))

    def get_graph_context(self, entities: list[str], question: str = "") -> str:
        """Retrieve graph paths, relation-aware facts, and text evidence.

        Args:
            entities: Linked entity names.
            question: Original question.

        Returns:
            Combined retrieval context.
        """
        relation_terms = self._detect_relation_terms(question)
        context_parts: list[str] = []

        if entities:
            try:
                with self.driver.session() as session:
                    context_parts.extend(self._get_shortest_paths(session, entities))
                    context_parts.extend(
                        self._get_relation_aware_neighborhood(
                            session=session,
                            entities=entities,
                            relation_terms=relation_terms,
                        )
                    )
            except Exception as exc:
                context_parts.append(f"GRAPH_WARNING: Neo4j context unavailable: {exc}")

        context_parts.extend(
            self.hybrid_retriever.retrieve(
                question=question,
                entities=entities,
                relation_terms=relation_terms,
                top_k=6,
            )
        )
        return "\n".join(list(dict.fromkeys(context_parts)))

    def query(self, question: str) -> dict[str, Any]:
        """Run GraphRAG query.

        Args:
            question: User question.

        Returns:
            Dict containing answer, retrieval context, and extracted entities.
        """
        entities = self.extract_entities(question)
        graph_context = self.get_graph_context(entities, question)

        if not graph_context:
            return {
                "answer": "Tôi không tìm thấy dữ liệu liên quan trong đồ thị.",
                "context": "",
                "entities": entities,
            }

        prompt = f"""You are a graph reasoning assistant.
Answer only from GRAPH FACT, PATH, and SOURCE_EVIDENCE below.
For multi-hop questions, explicitly follow the chain.
If SOURCE_EVIDENCE contradicts a noisy graph relation, prefer SOURCE_EVIDENCE.
Return a concise Vietnamese answer.

CONTEXT:
{graph_context}

QUESTION: {question}
ANSWER:"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return {
                "answer": response.content,
                "context": graph_context,
                "entities": entities,
            }
        except Exception as exc:
            return {
                "answer": f"Lỗi: {exc}",
                "context": graph_context,
                "entities": entities,
            }

    def _load_graph_node_names(self) -> list[str]:
        """Load canonical node names from Neo4j.

        Returns:
            Deduplicated graph node names.
        """
        query = "MATCH (n) RETURN DISTINCT n.name AS name"
        try:
            with self.driver.session() as session:
                return [row["name"] for row in session.run(query) if row["name"]]
        except Exception:
            return []

    def _load_triple_node_names(self, triples_path: str = "data/triples.json") -> list[str]:
        """Load canonical node names from triples as Neo4j fallback.

        Args:
            triples_path: Path to extracted triples JSON.

        Returns:
            Deduplicated subject/object names.
        """
        path = Path(triples_path)
        if not path.exists():
            return []
        try:
            triples = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        names: list[str] = []
        for triple in triples:
            if not isinstance(triple, dict):
                continue
            subject = str(triple.get("subject", "")).strip()
            obj = str(triple.get("object", "")).strip()
            if subject:
                names.append(subject)
            if obj:
                names.append(obj)
        return list(dict.fromkeys(names))

    def _extract_raw_entities(self, question: str) -> list[str]:
        """Use LLM to extract raw entities without benchmark-specific hints.

        Args:
            question: User question.

        Returns:
            Raw entity mentions.
        """
        prompt = f"""Extract named entities and noun phrases needed for graph lookup.
Return comma-separated names only. Do not answer the question.
Include products, companies, people, technologies, dates, and key noun phrases.

Question: {question}
Entities:"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            entities = [
                entity.strip()
                for entity in response.content.split(",")
                if entity.strip() and entity.strip().lower() != "none"
            ]
        except Exception:
            entities = []

        entities.extend(self._extract_surface_mentions(question))
        return list(dict.fromkeys(entities))

    def _extract_surface_mentions(self, question: str) -> list[str]:
        """Extract generic surface mentions as fallback.

        Args:
            question: User question.

        Returns:
            Candidate mentions based on capitalization and known aliases.
        """
        mentions: list[str] = []
        tokens = question.replace("?", "").replace(",", " ").split()
        current: list[str] = []
        for token in tokens:
            clean = token.strip("'\"()[]{}")
            if clean[:1].isupper() or any(char.isdigit() for char in clean) or "-" in clean:
                current.append(clean)
            elif current:
                mention = " ".join(current)
                if self.entity_normalizer.normalize_text(mention) not in QUESTION_STOPWORDS:
                    mentions.append(mention)
                current = []
        if current:
            mention = " ".join(current)
            if self.entity_normalizer.normalize_text(mention) not in QUESTION_STOPWORDS:
                mentions.append(mention)

        normalized_question = self.entity_normalizer.normalize_text(question)
        for alias, canonical in self.entity_normalizer.alias_to_canonical.items():
            if len(alias) >= 4 and alias in normalized_question:
                mentions.append(canonical)
        return list(dict.fromkeys(mentions))

    def _detect_relation_terms(self, question: str) -> list[str]:
        """Detect relation-intent terms from question.

        Args:
            question: User question.

        Returns:
            Relation names and textual intent terms.
        """
        q = question.lower()
        terms: list[str] = []
        if any(word in q for word in ["ceo", "chief executive", "replaced", "succeeded"]):
            terms.extend(["CEO_OF", "EMPLOYED_BY", "chief executive officer", "appointed CEO"])
        if any(word in q for word in ["cloud", "platform", "infrastructure", "azure"]):
            terms.extend(["USES_TECHNOLOGY", "PARTNER_WITH", "Microsoft Azure", "cloud platform"])
        if any(word in q for word in ["invested", "investment", "stake", "owned", "holds"]):
            terms.extend(["INVESTED_IN", "ACQUIRED", "stake", "owned", "holds"])
        if any(word in q for word in ["founded", "co-founded", "founder"]):
            terms.extend(["FOUNDED_BY", "CO_FOUNDED", "founded"])
        if any(word in q for word in ["headquartered", "where"]):
            terms.extend(["HEADQUARTERED_IN", "location"])
        if any(word in q for word in ["developed", "created", "released", "products"]):
            terms.extend(["DEVELOPED", "released", "created"])
        if any(word in q for word in ["parent", "subsidiary", "owns", "owned by"]):
            terms.extend(["ACQUIRED", "parent company", "subsidiary", "owned"])
        return list(dict.fromkeys(terms))

    def _get_shortest_paths(self, session: Any, entities: list[str]) -> list[str]:
        """Get shortest paths between linked entities for multi-hop reasoning."""
        if len(entities) < 2:
            return []

        context: list[str] = []
        query = """
        MATCH (n1 {name: $e1}), (n2 {name: $e2})
        WHERE n1 <> n2
        MATCH p = shortestPath((n1)-[*..4]-(n2))
        RETURN p
        LIMIT 3
        """
        for i, entity_1 in enumerate(entities[:10]):
            for entity_2 in entities[i + 1 : 10]:
                for record in session.run(query, e1=entity_1, e2=entity_2):
                    context.append(self._format_path(record["p"]))
        return context

    def _get_relation_aware_neighborhood(
        self,
        session: Any,
        entities: list[str],
        relation_terms: list[str],
    ) -> list[str]:
        """Retrieve and rank directed neighborhood facts by relation intent."""
        query = """
        MATCH (n {name: $name})-[r1]-(m)
        OPTIONAL MATCH (m)-[r2]-(k)
        RETURN
            startNode(r1).name AS r1_start,
            type(r1) AS r1_type,
            endNode(r1).name AS r1_end,
            startNode(r2).name AS r2_start,
            type(r2) AS r2_type,
            endNode(r2).name AS r2_end
        LIMIT 120
        """
        scored: list[tuple[int, str]] = []
        for entity in entities[:12]:
            for row in session.run(query, name=entity):
                line = f"FACT: {row['r1_start']} --{row['r1_type']}--> {row['r1_end']}"
                score = self._score_fact(line, relation_terms)
                if row["r2_type"] and row["r2_start"] and row["r2_end"]:
                    second = f"{row['r2_start']} --{row['r2_type']}--> {row['r2_end']}"
                    line += f"; {second}"
                    score += self._score_fact(second, relation_terms)
                scored.append((score, line))

        scored.sort(key=lambda item: item[0], reverse=True)
        return list(dict.fromkeys(line for _, line in scored[:80]))

    def _score_fact(self, fact: str, relation_terms: list[str]) -> int:
        """Score graph fact against relation intent terms."""
        fact_lower = fact.lower()
        score = 0
        for term in relation_terms:
            if term.lower() in fact_lower:
                score += 3
        if "--" in fact:
            score += 1
        return score

    def _format_path(self, path: Any) -> str:
        """Format Neo4j path with relation names."""
        nodes = [node["name"] for node in path.nodes]
        relations = [type(rel) for rel in path.relationships]
        steps = [nodes[0]]
        for relation, node in zip(relations, nodes[1:]):
            steps.append(f"--{relation}-->")
            steps.append(node)
        return f"PATH: {' '.join(steps)}"
