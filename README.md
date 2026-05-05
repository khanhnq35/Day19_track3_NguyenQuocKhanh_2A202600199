# GraphRAG: Hybrid Retrieval-Augmented Generation for Tech Company Corpus

> **Author:** Nguyễn Quốc Khánh — 2A202600199  
> **Date:** 05/05/2026  
> **Phase 2 — Day 19:** Graph-based RAG with Knowledge Graph Reasoning

---

## 📌 Tổng quan dự án

Dự án triển khai hệ thống **Hybrid GraphRAG** kết hợp ba chiến lược truy xuất tri thức để trả lời câu hỏi phức tạp về các công ty công nghệ:

| Hệ thống | Cơ chế | Điểm mạnh |
|---|---|---|
| **Flat RAG** | Vector similarity search (ChromaDB) | Nhanh, đơn giản, tốt cho single-hop |
| **Graph RAG** | Knowledge Graph traversal (Neo4j) | Multi-hop reasoning, mối quan hệ cấu trúc |
| **Hybrid RAG** | Kết hợp Vector + Graph → LLM Synthesis | Tối ưu cả single-hop lẫn multi-hop |

---

## 🏗️ Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CORPUS (Raw Text)                            │
│              data/tech_company_corpus.txt (~237 KB)                 │
└────────────────┬──────────────────────────┬─────────────────────────┘
                 │                          │
      ┌──────────▼──────────┐    ┌──────────▼──────────────┐
      │    FLAT RAG PATH    │    │    GRAPH RAG PATH       │
      │                     │    │                         │
      │  Text Chunking      │    │  LLM Triple Extraction  │
      │  (Recursive 1000)   │    │  (Entity + Relation)    │
      │       │             │    │       │                 │
      │       ▼             │    │       ▼                 │
      │  Vertex AI          │    │  Entity Normalization   │
      │  Embedding          │    │  (Alias + Fuzzy Match)  │
      │  (text-embedding-   │    │       │                 │
      │   004)              │    │       ▼                 │
      │       │             │    │  Neo4j Graph Build      │
      │       ▼             │    │  (MERGE nodes + edges)  │
      │  ChromaDB           │    │       │                 │
      │  Vector Store       │    │       ▼                 │
      └───────┬─────────────┘    │  Graph Query Engine     │
              │                  │  - Shortest Path        │
              │                  │  - Relation-Aware       │
              │                  │    Neighborhood          │
              │                  │  - BM25 Text Evidence   │
              │                  └──────────┬──────────────┘
              │                             │
      ┌───────▼─────────────────────────────▼──────────────┐
      │                  HYBRID RAG                         │
      │                                                    │
      │   ┌──────────┐         ┌──────────┐                │
      │   │  Vector   │         │  Graph   │                │
      │   │  Context  │         │  Context │                │
      │   └────┬─────┘         └────┬─────┘                │
      │        │                    │                       │
      │        └────────┬───────────┘                       │
      │                 ▼                                   │
      │         Merge & Deduplicate                         │
      │                 │                                   │
      │                 ▼                                   │
      │    Vertex AI LLM (gemini-2.5-flash)                 │
      │         Synthesized Answer                           │
      └─────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc dự án

```
Day19_NguyenQuocKhanh_2A202600199/
├── src/                          # Mã nguồn chính
│   ├── config.py                 # Cấu hình môi trường (GCP, Neo4j)
│   ├── data_fetcher.py           # Thu thập dữ liệu từ Wikipedia
│   ├── entity_extraction.py      # LLM-based triple extraction
│   ├── entity_normalizer.py      # Entity linking & normalization
│   ├── graph_builder.py          # Neo4j graph construction
│   ├── graph_query.py            # GraphRAG query engine
│   ├── flat_rag.py               # Vector-based RAG (ChromaDB)
│   ├── hybrid_rag.py             # Hybrid RAG engine (Vector + Graph)
│   ├── hybrid_retriever.py       # BM25 evidence retriever
│   └── evaluation.py             # 3-way benchmark evaluation
├── data/
│   ├── tech_company_corpus.txt   # Corpus thô (~237 KB)
│   ├── triples.json              # Extracted knowledge triples (~105 KB)
│   └── chroma_db/                # Persisted vector store
├── benchmark/
│   └── questions.json            # 20 câu hỏi benchmark
├── results/
│   ├── eval_results.json         # Kết quả đánh giá chi tiết
│   ├── comparison_table.md       # Bảng so sánh 3 hệ thống
│   └── cost_analysis.md          # Phân tích chi phí build & inference
├── run_pipeline.py               # Pipeline runner (end-to-end)
├── docker-compose.yml            # Neo4j Docker config
└── requirements.txt              # Python dependencies
```

---

## 🔍 Chi tiết từng hệ thống

### 1. Flat RAG — Vector Similarity Retrieval

**Luồng hoạt động:**

```
Corpus Text
    │
    ▼
RecursiveCharacterTextSplitter
(chunk_size=1000, overlap=200)
    │
    ▼
VertexAI Embeddings
(model: text-embedding-004)
    │
    ▼
ChromaDB Vector Store
    │
    ▼
similarity_search(query, k=4)
    │
    ▼
LLM Answer Generation
```

**Triển khai:** [`src/flat_rag.py`](src/flat_rag.py)

- **Chunking:** `RecursiveCharacterTextSplitter` với `chunk_size=1000`, `chunk_overlap=200`
- **Embedding:** Google `text-embedding-004` qua Vertex AI
- **Vector Store:** ChromaDB (persistent, lưu tại `data/chroma_db/`)
- **Retrieval:** Top-4 similarity search → context đưa thẳng vào LLM

**Ưu điểm:** Nhanh (avg ~3.2s), đơn giản, hiệu quả cho câu hỏi single-hop  
**Hạn chế:** Không thể reasoning qua nhiều bước liên kết (multi-hop accuracy chỉ ~0.14)

---

### 2. Graph RAG — Knowledge Graph Reasoning

**Luồng hoạt động:**

```
Corpus Text
    │
    ▼
EntityExtractor (LLM)
│  - Coreference Resolution
│  - Triple Extraction
│  Format: Subject | Label | Relation | Object | Label
│
    ▼
EntityNormalizer
│  - Alias Generation (legal suffix, acronym, parentheses)
│  - Fuzzy Matching (SequenceMatcher, cutoff=0.78)
│  - Substring Matching
│
    ▼
GraphBuilder
│  - Schema Enforcement (6 labels, 11 relations)
│  - MERGE-based upsert (dedup auto)
│  - Unique constraints per label
│
    ▼
Neo4j Knowledge Graph
    │
    ▼
GraphQueryEngine
│  ├── Entity Extraction from Question (LLM + surface mentions)
│  ├── Entity Linking → canonical names
│  ├── Shortest Path (multi-hop, depth ≤ 4)
│  ├── Relation-Aware Neighborhood (scored by intent)
│  └── BM25 Text Evidence (HybridEvidenceRetriever)
│
    ▼
LLM Answer Generation
```

**Triển khai:** [`src/graph_query.py`](src/graph_query.py), [`src/graph_builder.py`](src/graph_builder.py)

#### 2.1 Entity Extraction (`entity_extraction.py`)

LLM trích xuất triples với coreference resolution:

```
Input:  "OpenAI was co-founded by Sam Altman. The company uses Microsoft Azure."
Output: OpenAI | COMPANY | CO_FOUNDED | Sam Altman | PERSON
        OpenAI | COMPANY | USES_TECHNOLOGY | Microsoft Azure | TECHNOLOGY
```

**Schema cứng:**
- **Node Labels:** `COMPANY`, `PERSON`, `PRODUCT`, `TECHNOLOGY`, `YEAR`, `LOCATION`
- **Relations:** `FOUNDED_BY`, `CEO_OF`, `DEVELOPED`, `ACQUIRED`, `INVESTED_IN`, `PARTNER_WITH`, `HEADQUARTERED_IN`, `FOUNDED_IN`, `USES_TECHNOLOGY`, `EMPLOYED_BY`, `CO_FOUNDED`

#### 2.2 Entity Normalization (`entity_normalizer.py`)

Entity linking generic, không hard-code benchmark tricks:

```
"Microsoft"          → exact match → "Microsoft"
"MSFT"               → acronym    → "Microsoft"  
"Google Inc"         → suffix strip → "Google"
"Alphabet"           → substring  → "Alphabet Inc."
"the ChatGPT maker"  → fuzzy      → "OpenAI"
```

**Alias generation strategies:**
1. Exact name & normalized form
2. Parenthetical extraction: `"Alphabet Inc. (Google)"` → `["Alphabet Inc.", "Google"]`
3. Legal suffix removal: `"Alphabet Inc."` → `"Alphabet"`
4. Initialism: `"International Business Machines"` → `"IBM"`
5. Acronym detection: uppercase tokens `≥ 2` chars

**Matching cascade:** Exact → Substring → Fuzzy (`SequenceMatcher`, cutoff `0.78`)

#### 2.3 Graph Query Engine (`graph_query.py`)

Truy vấn đồ thị với 3 chiến lược:

| Strategy | Description | Use Case |
|---|---|---|
| **Shortest Path** | `shortestPath((n1)-[*..4]-(n2))` | Multi-hop: "CEO of company that developed ChatGPT" |
| **Relation-Aware Neighborhood** | 1-hop + 2-hop facts, scored by relation intent | Single-hop với context bổ sung |
| **BM25 Text Evidence** | Sentence-level retrieval từ corpus gốc | Numeric facts, quotes, fallback |

**Relation detection:** Question keywords → graph relation mapping  
```
"CEO" → [CEO_OF, EMPLOYED_BY]
"invested" → [INVESTED_IN, ACQUIRED]  
"founded" → [FOUNDED_BY, CO_FOUNDED]
```

---

### 3. Hybrid RAG — Combined Retrieval

**Luồng hoạt động:**

```
User Question
    │
    ├─── FlatRAG.similarity_search(k=4)  ──→  Vector Context
    │
    ├─── GraphQueryEngine.extract_entities()
    │         │
    │         └──→ GraphQueryEngine.get_graph_context()
    │                  │
    │                  ├── Shortest Paths
    │                  ├── Relation-Aware Facts  
    │                  └── BM25 Evidence ──→  Graph Context
    │
    ▼
_merge_contexts()
    │  === GRAPH EVIDENCE ===
    │  {graph_context}
    │  
    │  === VECTOR EVIDENCE ===  
    │  {vector_context}
    │
    ▼
LLM Synthesis Prompt
│  "For multi-hop questions, follow graph paths 
│   but verify facts against vector text.
│   Prefer graph FACTS for structured relationships.
│   Prefer SOURCE_EVIDENCE for numeric details."
│
    ▼
Final Answer
```

**Triển khai:** [`src/hybrid_rag.py`](src/hybrid_rag.py)

**Merge strategy:** Concatenation with section headers (`GRAPH EVIDENCE` / `VECTOR EVIDENCE`). Weight parameters (`vector_weight=0.4`, `graph_weight=0.6`) reserved cho future scoring enhancements.

---

## 📊 Kết quả đánh giá

### Benchmark: 30 câu hỏi (10 single-hop, 10 multi-hop, 10 complex-reasoning)

**Metrics:** Correctness (C), Faithfulness (F), No-Hallucination (H) — đánh giá bằng LLM Judge (gemini-2.5-flash)

### Accuracy theo Category

| Category | Flat RAG | Graph RAG | Hybrid RAG | Best System |
|---|:---:|:---:|:---:|:---:|
| **Single-hop** | 0.80 | 0.90 | **1.00** | **Hybrid** |
| **Multi-hop** | 0.30 | **0.91** | 0.80 | **Graph** |
| **Complex-reasoning** | 0.49 | 0.64 | **0.80** | **Hybrid** |
| **Overall (Avg)** | 0.53 | 0.82 | **0.87** | **Hybrid** |

### Cost & Performance

| Chỉ số (Indicator) | Flat RAG | Graph RAG | Hybrid RAG |
|---|:---:|:---:|:---:|
| **Accuracy (Avg)** | 0.53 | 0.82 | **0.87** |
| **Response Time (Avg)** | **3.71s** | 9.49s | 8.99s |
| **Latency (P95)** | **7.14s** | 16.72s | 18.05s |
| **Context Size (Avg chars)** | 2,808 | 7,525 | 10,356 |
| **Faithfulness (Avg)** | 0.97 | 0.96 | **1.00** |
| **No-Hallucination (Avg)** | **0.97** | 0.97 | 0.80 |

### Build Cost

| Pipeline | Build Time (s) | Build Tokens (est.) |
|---|---:|---:|
| **FlatRAG** | **22.18s** | 59,297 |
| **GraphRAG** | 679.40s | 111,703 |

> **Nhận xét:** 
> - **Hybrid RAG** đạt độ chính xác tổng thể cao nhất (**0.87**) nhờ kết hợp ưu điểm của cả hai phương pháp.
> - **Graph RAG** vượt trội hoàn toàn ở các câu hỏi **Multi-hop** (+61% so với Flat).
> - **Flat RAG** vẫn duy trì lợi thế về tốc độ phản hồi (latency thấp hơn ~2.5x).


---

## 🛠️ Công nghệ sử dụng

| Component | Technology |
|---|---|
| **LLM** | Vertex AI — `gemini-2.5-flash` |
| **Embeddings** | Vertex AI — `text-embedding-004` |
| **Vector Store** | ChromaDB (persistent) |
| **Knowledge Graph** | Neo4j 5 (Docker) |
| **Framework** | LangChain + LangChain-Google-VertexAI |
| **Language** | Python 3.9+ |
| **Auth** | GCP Application Default Credentials (ADC) |

---

## 🚀 Hướng dẫn cài đặt & chạy

### 1. Cài đặt môi trường

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Chạy Neo4j

```bash
docker-compose up -d
```

### 3. Thiết lập biến môi trường

Tạo file `.env` từ `.env.example`:

```env
GCP_PROJECT_ID=gen-lang-client-0610024827
GCP_LOCATION=us-central1
GCP_MODEL_NAME=gemini-2.5-flash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag2024
```

### 4. Xác thực GCP

```bash
gcloud auth application-default login
```

### 5. Chạy Pipeline đầy đủ

```bash
# Full pipeline (fetch → extract → build → evaluate)
python run_pipeline.py

# Bỏ qua fetch (dùng corpus có sẵn)
python run_pipeline.py --skip-fetch

# Chỉ chạy evaluation (đã có graph sẵn)
python run_pipeline.py --skip-fetch --skip-graph-build
```

### 6. Chạy riêng lẻ từng module

```bash
# Triple extraction
python -m src.entity_extraction

# Build Neo4j graph
python -m src.graph_builder

# Run evaluation benchmark
python -m src.evaluation
```

---

## 📖 Tài liệu tham khảo

- [Lab Day 19 Instructions](lab_day_19_graphrag_tech_company_corpus.md)
- [Implementation Plan](Implementation_plan.md)
- [Evaluation Results](results/eval_results.json)
- [Comparison Table](results/comparison_table.md)
- [Cost Analysis](results/cost_analysis.md)

---

**Tác giả:** Nguyễn Quốc Khánh — 2A202600199  
**Ngày thực hiện:** 05/05/2026
