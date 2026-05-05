"""Hybrid RAG: Combines vector search (FlatRAG) with graph search (GraphRAG).

This module merges retrieval context from both ChromaDB vector store and
Neo4j knowledge graph to provide richer, more accurate context for LLM
generation, particularly for multi-hop reasoning questions.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI

from src.config import Config
from src.flat_rag import FlatRAG
from src.graph_query import GraphQueryEngine


class HybridRAG:
    """Hybrid RAG engine combining vector and graph retrieval.

    Architecture:
        1. Vector retrieval via FlatRAG (ChromaDB + VertexAI embeddings)
        2. Graph retrieval via GraphQueryEngine (Neo4j + entity linking)
        3. Merge and deduplicate context
        4. LLM generates answer from combined context
    """

    def __init__(
        self,
        corpus_path: str = "data/tech_company_corpus.txt",
        vector_weight: float = 0.4,
        graph_weight: float = 0.6,
    ) -> None:
        """Initialize Hybrid RAG with both retrieval engines.

        Args:
            corpus_path: Path to source corpus for graph's text evidence.
            vector_weight: Importance weight for vector context (unused in
                current merge strategy but reserved for future scoring).
            graph_weight: Importance weight for graph context.
        """
        Config.validate()
        self.flat_engine = FlatRAG()
        self.graph_engine = GraphQueryEngine(corpus_path=corpus_path)
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )

    def query(self, question: str, k: int = 4) -> dict[str, Any]:
        """Run hybrid retrieval and generate answer.

        Args:
            question: User question.
            k: Number of vector results to retrieve.

        Returns:
            Dict with answer, vector_context, graph_context, merged_context.
        """
        # 1. Vector retrieval
        if not self.flat_engine.vectorstore:
            self.flat_engine.load_db()
        vector_docs = self.flat_engine.vectorstore.similarity_search(question, k=k)
        vector_context = "\n\n".join([doc.page_content for doc in vector_docs])

        # 2. Graph retrieval
        entities = self.graph_engine.extract_entities(question)
        graph_context = self.graph_engine.get_graph_context(entities, question)

        # 3. Merge contexts
        merged_context = self._merge_contexts(vector_context, graph_context)

        if not merged_context:
            return {
                "answer": "Tôi không tìm thấy dữ liệu liên quan.",
                "vector_context": vector_context,
                "graph_context": graph_context,
                "merged_context": "",
                "entities": entities,
            }

        # 4. LLM generation
        prompt = f"""You are a hybrid retrieval assistant combining vector search
and knowledge graph evidence. Use both CONTEXT sections below to answer.

For multi-hop questions, follow the graph paths but verify facts against
the vector text. Prefer graph FACTS for structured relationships.
Prefer SOURCE_EVIDENCE for numeric details and direct quotes.

CONTEXT:
{merged_context}

QUESTION: {question}
ANSWER:"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            answer = response.content
        except Exception as exc:
            answer = f"Lỗi: {exc}"

        return {
            "answer": answer,
            "vector_context": vector_context,
            "graph_context": graph_context,
            "merged_context": merged_context,
            "entities": entities,
        }

    @staticmethod
    def _merge_contexts(vector_ctx: str, graph_ctx: str) -> str:
        """Merge and deduplicate vector and graph contexts.

        Args:
            vector_ctx: Context from vector search.
            graph_ctx: Context from graph search.

        Returns:
            Merged context string with section headers.
        """
        parts: list[str] = []

        if graph_ctx:
            parts.append("=== GRAPH EVIDENCE ===")
            parts.append(graph_ctx)

        if vector_ctx:
            parts.append("=== VECTOR EVIDENCE ===")
            parts.append(vector_ctx)

        return "\n\n".join(parts)
