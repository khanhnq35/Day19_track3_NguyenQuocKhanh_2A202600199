# Build Cost Report

| Stage | Time (s) | Input Tokens (est.) | Output Tokens (est.) | Total Tokens (est.) | Notes |
|---|---:|---:|---:|---:|---|
| flat_rag_build | 22.18 | 59,297 | 0 | 59,297 | FlatRAG Chroma embedding/index build. Token estimate = corpus tokens embedded. |
| graph_rag_triple_extraction | 676.79 | 59,297 | 26,203 | 85,500 | GraphRAG LLM triple extraction. Token estimate covers corpus input and triples output. |
| graph_rag_neo4j_build | 2.61 | 26,203 | 0 | 26,203 | Neo4j graph construction from triples; no LLM token cost beyond triples input proxy. |

## Build Summary

| Pipeline | Build Time (s) | Build Tokens (est.) |
|---|---:|---:|
| FlatRAG | 22.18 | 59,297 |
| GraphRAG | 679.40 | 111,703 |

> Token usage is estimated with `ceil(chars / 4)` because current LangChain calls do not expose provider usage metadata consistently.
