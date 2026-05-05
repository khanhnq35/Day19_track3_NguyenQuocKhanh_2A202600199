# Implementation Report: Hybrid GraphRAG for Tech Company Corpus

**Người thực hiện:** Nguyễn Quốc Khánh — 2A202600199  
**Ngày cập nhật:** 05/05/2026  
**Dự án:** Lab Day 19 — GraphRAG Tech Company Corpus

---

## 1. Mục tiêu triển khai

Dự án xây dựng hệ thống **Retrieval-Augmented Generation (RAG)** cho bộ dữ liệu về các công ty công nghệ, với trọng tâm là so sánh ba hướng truy xuất:

1. **Flat RAG:** truy xuất ngữ cảnh bằng vector similarity search.
2. **Graph RAG:** truy xuất tri thức bằng Knowledge Graph trên Neo4j.
3. **Hybrid RAG:** kết hợp Flat RAG và Graph RAG để tận dụng cả bằng chứng văn bản lẫn quan hệ cấu trúc.

Mục tiêu chính là chứng minh rằng GraphRAG và HybridRAG xử lý tốt hơn các câu hỏi **multi-hop** và **complex reasoning**, nơi câu trả lời cần nối nhiều thực thể và quan hệ khác nhau.

---

## 2. Kiến trúc hệ thống

### 2.1 Tổng quan pipeline

```text
Raw Corpus
    │
    ├── Flat RAG Path
    │      ├── Chunking
    │      ├── Vertex AI Embedding
    │      ├── ChromaDB Vector Store
    │      └── Similarity Retrieval
    │
    ├── Graph RAG Path
    │      ├── LLM Triple Extraction
    │      ├── Entity Normalization
    │      ├── Neo4j Graph Build
    │      ├── Shortest Path Retrieval
    │      ├── Relation-Aware Neighborhood
    │      └── BM25-like Text Evidence
    │
    └── Hybrid RAG Path
           ├── Retrieve Vector Context
           ├── Retrieve Graph Context
           ├── Merge Evidence
           └── LLM Answer Synthesis
```

### 2.2 Thành phần chính

| Thành phần | File | Vai trò |
|---|---|---|
| Config | `src/config.py` | Load cấu hình GCP Vertex AI và Neo4j |
| Data Fetcher | `src/data_fetcher.py` | Thu thập corpus từ Wikipedia |
| Entity Extractor | `src/entity_extraction.py` | Trích xuất triples bằng Gemini |
| Entity Normalizer | `src/entity_normalizer.py` | Chuẩn hóa và liên kết entity aliases |
| Graph Builder | `src/graph_builder.py` | Xây dựng Neo4j knowledge graph |
| Graph Query Engine | `src/graph_query.py` | Truy vấn graph bằng path và neighborhood |
| Flat RAG | `src/flat_rag.py` | Vector RAG baseline bằng ChromaDB |
| Hybrid Retriever | `src/hybrid_retriever.py` | BM25-like sentence evidence fallback |
| Hybrid RAG | `src/hybrid_rag.py` | Kết hợp Vector + Graph context |
| Evaluator | `src/evaluation.py` | Benchmark Flat/Graph/Hybrid RAG |
| Pipeline Runner | `run_pipeline.py` | Chạy end-to-end pipeline và cost report |

---

## 3. Phase 1 — Research & Design

Phase 1 tập trung làm rõ các nền tảng lý thuyết của GraphRAG:

### 3.1 Entity Extraction: Node vs Attribute

Hệ thống dùng **schema-guided prompting** để hướng dẫn LLM phân biệt:

- **Node:** thực thể có định danh và có thể tham gia quan hệ, ví dụ `OpenAI`, `Sam Altman`, `ChatGPT`.
- **Attribute:** thông tin mô tả thực thể, ví dụ năm thành lập, địa điểm, tỷ lệ sở hữu. Trong hệ thống này, một số attribute quan trọng như `YEAR` hoặc `LOCATION` được biểu diễn thành node để hỗ trợ traversal.

### 3.2 Deduplication trong graph

Deduplication quan trọng vì graph reasoning phụ thuộc vào tính liên thông. Nếu `OpenAI`, `Open AI`, và `OpenAI Inc.` bị tách thành nhiều node, path như sau có thể bị đứt:

```text
ChatGPT ──DEVELOPED_BY──> OpenAI ──CEO_OF──> Sam Altman
```

Vì vậy dự án bổ sung `EntityNormalizer` để giảm fragmentation và tăng khả năng multi-hop retrieval.

### 3.3 BFS / Graph Traversal vs Vector Search

| Tiêu chí | Vector Search | Graph Traversal |
|---|---|---|
| Cơ chế | Tìm chunk gần nghĩa với query | Duyệt node và relationship |
| Dữ liệu chính | Văn bản phi cấu trúc | Triples có cấu trúc |
| Mạnh ở | Single-hop, fact lookup | Multi-hop, relation reasoning |
| Yếu ở | Context rời rạc, thiếu chain | Tốn chi phí build graph |

---

## 4. Phase 2 — Environment Setup

### 4.1 Python environment

Dự án dùng `.venv` riêng để cô lập dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Ghi chú: command log hiện tại cho thấy môi trường đang chạy Python `3.9.6`, và Google SDK cảnh báo nên nâng cấp lên Python `3.10+`. Pipeline vẫn chạy thành công, nhưng để ổn định lâu dài nên dùng Python 3.10+.

### 4.2 Neo4j Docker

Neo4j chạy qua Docker Compose:

```bash
docker-compose up -d
```

Thông tin kết nối mặc định:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag2024
```

### 4.3 Vertex AI

Dự án dùng Google Vertex AI:

```env
GCP_PROJECT_ID=gen-lang-client-0610024827
GCP_LOCATION=us-central1
GCP_MODEL_NAME=gemini-2.5-flash
```

Cần xác thực Application Default Credentials:

```bash
gcloud auth application-default login
```

---

## 5. Phase 3 — Indexing Pipeline

Phase 3 biến corpus văn bản thành hai dạng index: **vector index** và **knowledge graph**.

### 5.1 Corpus collection

- Nguồn: Wikipedia và các chủ đề công nghệ.
- Số chủ đề: 26 công ty / tổ chức / sản phẩm công nghệ.
- File đầu ra: `data/tech_company_corpus.txt`.
- Dung lượng hiện tại: khoảng 237 KB.

Corpus này là đầu vào chung cho FlatRAG, GraphRAG và HybridRAG.

### 5.2 Flat RAG indexing

File triển khai: `src/flat_rag.py`

Quy trình:

```text
tech_company_corpus.txt
    │
    ▼
RecursiveCharacterTextSplitter
(chunk_size=1000, chunk_overlap=200)
    │
    ▼
VertexAIEmbeddings(text-embedding-004)
    │
    ▼
ChromaDB persistent store
(data/chroma_db/)
```

FlatRAG dùng top-k vector search:

```python
docs = self.vectorstore.similarity_search(question, k=4)
```

Ưu điểm là nhanh và dễ build. Hạn chế là nó chỉ thấy các chunk gần nghĩa nhất, không đảm bảo gom được nhiều mảnh thông tin nằm xa nhau trong corpus.

### 5.3 Triple extraction

File triển khai: `src/entity_extraction.py`

LLM prompt yêu cầu trích xuất theo định dạng:

```text
Subject | Subject_Label | Relation | Object | Object_Label
```

Schema entity labels:

```text
COMPANY, PERSON, PRODUCT, TECHNOLOGY, YEAR, LOCATION
```

Schema relations:

```text
FOUNDED_BY, CEO_OF, DEVELOPED, ACQUIRED, INVESTED_IN,
PARTNER_WITH, HEADQUARTERED_IN, FOUNDED_IN,
USES_TECHNOLOGY, EMPLOYED_BY, CO_FOUNDED
```

Prompt có thêm yêu cầu **coreference resolution** trước khi xuất triple. Ví dụ:

```text
Input:
OpenAI developed ChatGPT. The company uses Microsoft Azure.

Expected triples:
OpenAI | COMPANY | DEVELOPED | ChatGPT | PRODUCT
OpenAI | COMPANY | USES_TECHNOLOGY | Microsoft Azure | TECHNOLOGY
```

Điểm quan trọng: đại từ hoặc cụm thay thế như `the company`, `it`, `they` được quy về entity cụ thể khi ngữ cảnh rõ ràng.

### 5.4 Entity normalization

File triển khai: `src/entity_normalizer.py`

Mục tiêu là giảm node duplicate và tăng khả năng link câu hỏi về đúng node graph.

Chiến lược alias:

| Chiến lược | Ví dụ |
|---|---|
| Normalize lowercase | `OpenAI` → `openai` |
| Legal suffix removal | `Alphabet Inc.` → `Alphabet` |
| Parentheses extraction | `Alphabet Inc. (Google)` → `Google` |
| Acronym detection | `International Business Machines` → `IBM` |
| Substring matching | `Alphabet` → `Alphabet Inc.` |
| Fuzzy matching | typo / biến thể tên gần đúng |

Matching cascade:

```text
Exact Match → Substring Match → Fuzzy Match
```

Fuzzy matching dùng `difflib.SequenceMatcher` và `get_close_matches` với cutoff `0.78`.

### 5.5 Neo4j graph build

File triển khai: `src/graph_builder.py`

Quy trình build graph:

1. Load triples từ `data/triples.json`.
2. Tạo unique constraints theo từng label.
3. Chuẩn hóa subject/object bằng `EntityNormalizer`.
4. Insert vào Neo4j bằng Cypher `MERGE`.
5. Verify số lượng nodes và relationships.

Cypher pattern:

```cypher
MERGE (s:LABEL {name: $subject})
MERGE (o:LABEL {name: $object})
MERGE (s)-[r:RELATION]->(o)
```

`MERGE` giúp graph build idempotent: chạy lại không tạo duplicate relationship giống hệt.

---

## 6. Phase 4 — Query Engine

### 6.1 GraphRAG query flow

File triển khai: `src/graph_query.py`

```text
Question
    │
    ▼
Extract raw entities
(LLM + surface mention fallback)
    │
    ▼
Entity linking
(EntityNormalizer)
    │
    ▼
Retrieve graph context
    ├── Shortest paths between entities
    ├── Relation-aware neighborhood
    └── BM25-like source evidence
    │
    ▼
LLM answer generation
```

### 6.2 Entity extraction from question

GraphQueryEngine dùng hai nguồn:

1. LLM extraction: lấy named entities và noun phrases.
2. Surface mention extraction: heuristic dựa trên capitalization, digit, hyphen và alias có sẵn.

Sau đó dùng `EntityNormalizer.link_entities()` để map về canonical graph node names.

### 6.3 Shortest path retrieval

Với nhiều entity trong câu hỏi, engine tìm đường ngắn nhất giữa từng cặp entity:

```cypher
MATCH (n1 {name: $e1}), (n2 {name: $e2})
WHERE n1 <> n2
MATCH p = shortestPath((n1)-[*..4]-(n2))
RETURN p
LIMIT 3
```

Cơ chế này hỗ trợ câu hỏi multi-hop như:

```text
Who is the CEO of the company that developed ChatGPT?
```

Graph có thể nối:

```text
ChatGPT → OpenAI → Sam Altman
```

### 6.4 Relation-aware neighborhood

Ngoài shortest path, hệ thống lấy 1-hop và 2-hop facts quanh entity:

```text
(n)-[r1]-(m)
(m)-[r2]-(k)
```

Mỗi fact được score theo relation intent. Ví dụ:

| Query keyword | Relation terms |
|---|---|
| `ceo`, `chief executive` | `CEO_OF`, `EMPLOYED_BY` |
| `cloud`, `platform` | `USES_TECHNOLOGY`, `PARTNER_WITH` |
| `invested`, `stake` | `INVESTED_IN`, `ACQUIRED` |
| `founded` | `FOUNDED_BY`, `CO_FOUNDED` |

Nhờ đó context ưu tiên quan hệ phù hợp với ý định câu hỏi.

### 6.5 BM25-like text evidence fallback

File triển khai: `src/hybrid_retriever.py`

Graph triples không phù hợp để lưu mọi chi tiết dài như:

- tỷ lệ cổ phần,
- ngày tháng cụ thể,
- mô tả tái cấu trúc,
- câu trích dẫn dài,
- thông tin numeric.

Vì vậy `HybridEvidenceRetriever` tách corpus thành câu và scoring bằng BM25-like formula. Kết quả được thêm vào graph context dưới prefix:

```text
SOURCE_EVIDENCE: ...
```

Cơ chế này giúp GraphRAG vừa có structured facts vừa có text evidence để kiểm chứng.

---

## 7. Phase 4 mở rộng — Hybrid RAG

File triển khai: `src/hybrid_rag.py`

### 7.1 Lý do thêm HybridRAG

FlatRAG tốt khi câu trả lời nằm trực tiếp trong một vài chunk gần query. GraphRAG tốt khi cần nối nhiều quan hệ. Tuy nhiên:

- Graph triples có thể mất chi tiết văn bản.
- Vector retrieval có thể thiếu liên kết logic.
- HybridRAG kết hợp cả hai để tăng coverage.

### 7.2 Hybrid query flow

```text
Question
    │
    ├── FlatRAG vector retrieval
    │      └── vector_context
    │
    ├── GraphRAG retrieval
    │      └── graph_context
    │
    ▼
Merge contexts
    ├── GRAPH EVIDENCE
    └── VECTOR EVIDENCE
    │
    ▼
LLM synthesis
```

### 7.3 Prompt synthesis

Prompt HybridRAG hướng dẫn LLM:

- dùng graph paths cho multi-hop reasoning,
- kiểm chứng facts bằng vector text,
- ưu tiên graph facts cho quan hệ có cấu trúc,
- ưu tiên source evidence cho numeric details và quote.

Đây là điểm khác biệt chính so với FlatRAG và GraphRAG riêng lẻ.

---

## 8. Phase 5 — Benchmark & Evaluation

### 8.1 Benchmark dataset

File: `benchmark/questions.json`

Bộ benchmark gồm 20 câu hỏi:

| Category | Số câu | Mục đích |
|---|---:|---|
| Single-hop | 10 | Kiểm tra fact lookup trực tiếp |
| Multi-hop | 7 | Kiểm tra nối nhiều entity/relationship |
| Complex-reasoning | 3 | Kiểm tra reasoning dài và so sánh quan hệ |

Ví dụ multi-hop:

```text
Who is the CEO of the company that developed ChatGPT?
```

Ví dụ complex reasoning:

```text
Alphabet and OpenAI both have connections to Microsoft.
How does Microsoft's relationship differ with each of these two companies?
```

### 8.2 Evaluation logic

File: `src/evaluation.py`

Mỗi câu hỏi được chạy qua ba hệ thống:

1. `FlatRAG.query()`
2. `GraphQueryEngine.query()`
3. `HybridRAG.query()`

Sau đó dùng LLM-as-a-judge chấm ba metric:

| Metric | Ý nghĩa |
|---|---|
| Correctness | Câu trả lời có khớp ground truth không |
| Faithfulness | Câu trả lời có dựa trên context truy xuất không |
| No-Hallucination | Câu trả lời có tránh bịa thông tin không |

Điểm nằm trong khoảng `[0.0, 1.0]`.

### 8.3 Concurrency và 429 retry

Benchmark chạy với `ThreadPoolExecutor(max_workers=4)`. Trong quá trình chạy có xuất hiện:

```text
ResourceExhausted: 429 Resource exhausted. Please try again later.
```

Đây là rate limit từ Vertex AI, không phải lỗi logic LangChain. LangChain tự retry và benchmark vẫn hoàn thành:

```text
✅ Xong câu 20
✅ Reports updated.
```

Nếu cần chạy ổn định hơn, có thể giảm `max_workers` xuống `1` hoặc `2`, hoặc thêm delay giữa các request.

---

## 9. Kết quả thực nghiệm

Kết quả mới nhất nằm trong:

- `results/eval_results.json`
- `results/comparison_table.md`
- `results/cost_analysis.md`

### 9.1 Accuracy theo nhóm câu hỏi

| Category | Flat RAG | GraphRAG | HybridRAG | Best System |
|---|---:|---:|---:|---|
| Single-hop | 0.92 | 0.80 | **1.00** | Hybrid |
| Multi-hop | 0.14 | **1.00** | **1.00** | Graph / Hybrid |
| Complex-reasoning | 0.43 | **0.93** | 0.83 | Graph |
| **Overall** | **0.57** | **0.89** | **0.97** | **Hybrid** |

### 9.2 Nhận xét accuracy

- **FlatRAG** đạt tốt ở single-hop nhưng giảm mạnh ở multi-hop (`0.14`). Nguyên nhân là vector search khó gom đủ các chunk chứa chuỗi quan hệ cần thiết.
- **GraphRAG** đạt `1.00` ở multi-hop vì path traversal nối được entity và relation.
- **HybridRAG** đạt overall cao nhất (`0.97`) vì kết hợp structured graph evidence và raw text evidence.
- Ở complex reasoning, GraphRAG (`0.93`) cao hơn HybridRAG (`0.83`) trong lần chạy này, cho thấy thêm context vector đôi khi có thể làm prompt dài hơn và gây nhiễu nhẹ.

### 9.3 Cost & performance

| Chỉ số | Flat RAG | Graph RAG | Hybrid RAG |
|---|---:|---:|---:|
| Accuracy Avg | 0.57 | 0.89 | **0.97** |
| Response Time Avg | 7.04s | 7.04s | 8.70s |
| Latency P95 | 13.37s | **10.19s** | 18.08s |
| Context Size Avg | 2,809 chars | 7,274 chars | 10,191 chars |
| Faithfulness Avg | 0.85 | **1.00** | **1.00** |
| No-Hallucination Avg | **0.95** | **0.95** | 0.90 |

### 9.4 Nhận xét performance

- HybridRAG có context lớn nhất vì ghép cả graph và vector evidence.
- HybridRAG latency cao hơn do phải chạy cả hai nhánh retrieval và prompt dài hơn.
- GraphRAG có context lớn hơn FlatRAG nhưng latency P95 thấp hơn FlatRAG trong lần chạy này, có thể do khác biệt retry/rate-limit và độ dài câu hỏi.
- Faithfulness của GraphRAG và HybridRAG đạt `1.00`, phản ánh context truy xuất giàu bằng chứng hơn FlatRAG.

---

## 10. Case study

### 10.1 Multi-hop: CEO của công ty phát triển ChatGPT

**Question:**

```text
Who is the CEO of the company that developed ChatGPT?
```

**Reasoning chain mong muốn:**

```text
ChatGPT ──DEVELOPED_BY / DEVELOPED──> OpenAI ──CEO_OF──> Sam Altman
```

**FlatRAG:** có thể tìm thấy chunk nói về ChatGPT hoặc OpenAI, nhưng không đảm bảo chunk đó cũng chứa CEO.  
**GraphRAG:** nối quan hệ trong graph, nên trả lời chính xác.  
**HybridRAG:** dùng graph chain và vector context để kiểm chứng.

### 10.2 Complex reasoning: Microsoft liên hệ với Alphabet và OpenAI

**Question:**

```text
Alphabet and OpenAI both have connections to Microsoft.
How does Microsoft's relationship differ with each of these two companies?
```

**Yêu cầu reasoning:**

- Nhận diện `Alphabet`, `OpenAI`, `Microsoft`.
- Tìm quan hệ Microsoft ↔ OpenAI.
- Tìm quan hệ Microsoft ↔ Alphabet.
- So sánh bản chất hai quan hệ.

HybridRAG đạt best ở câu này vì vừa có graph facts, vừa có vector evidence từ corpus gốc để diễn giải khác biệt.

---

## 11. Kết luận triển khai

### 11.1 Những gì đã hoàn thành

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Research report | ✅ Hoàn thành | `report/research.md` |
| Environment setup | ✅ Hoàn thành | `.venv`, Neo4j Docker, Vertex AI config |
| Corpus collection | ✅ Hoàn thành | `data/tech_company_corpus.txt` |
| FlatRAG index | ✅ Hoàn thành | ChromaDB persistent store |
| Triple extraction | ✅ Hoàn thành | `data/triples.json` |
| Neo4j graph build | ✅ Hoàn thành | Constraints + MERGE insertion |
| Entity normalization | ✅ Hoàn thành | Alias, substring, fuzzy matching |
| Graph query engine | ✅ Hoàn thành | shortest path + neighborhood + evidence |
| HybridRAG | ✅ Hoàn thành | Vector + Graph context merge |
| Evaluation | ✅ Hoàn thành | 20 questions, 3 systems |
| Reports | ✅ Hoàn thành | README, comparison, cost, implementation report |

### 11.2 Kết luận kỹ thuật

- **FlatRAG** là baseline tốt cho câu hỏi trực tiếp nhưng không đủ mạnh cho reasoning qua nhiều thực thể.
- **GraphRAG** cải thiện rõ rệt ở multi-hop nhờ biểu diễn tri thức dưới dạng node-edge.
- **HybridRAG** cho accuracy overall cao nhất nhờ kết hợp context cấu trúc và text evidence.
- Entity normalization là thành phần quan trọng để tránh graph fragmentation.
- BM25-like source evidence giúp bù phần thông tin khó biểu diễn bằng triples.

### 11.3 Hạn chế hiện tại

1. **Rate limit Vertex AI:** benchmark song song 4 luồng có thể gặp 429, dù retry đã xử lý được.
2. **Python version:** môi trường hiện tại là Python 3.9.6, Google SDK khuyến nghị Python 3.10+.
3. **Hybrid context dài:** context trung bình 10,191 chars, có thể gây latency cao và nhiễu prompt.
4. **LLM-as-judge variance:** điểm đánh giá có thể dao động giữa các lần chạy.
5. **Graph schema giới hạn:** chỉ dùng 6 labels và 11 relation types, chưa bao phủ mọi loại tri thức doanh nghiệp.

### 11.4 Hướng cải tiến

- Giảm `max_workers` hoặc thêm backoff để tránh 429 khi benchmark.
- Ranking lại merged context trong HybridRAG thay vì nối toàn bộ graph + vector evidence.
- Thêm confidence score cho triples từ LLM extraction.
- Thêm graph visualization screenshots vào báo cáo cuối.
- Chuẩn hóa môi trường lên Python 3.10+.
- Chuyển `langchain_community.vectorstores.Chroma` sang package `langchain-chroma` để tránh deprecation warning.

---

## 12. Final status

Dự án đã hoàn thành mục tiêu chính: xây dựng và đánh giá hệ thống **FlatRAG vs GraphRAG vs HybridRAG** trên Tech Company Corpus. Kết quả cho thấy HybridRAG đạt accuracy tổng thể cao nhất (`0.97`), trong khi GraphRAG thể hiện lợi thế rõ rệt ở multi-hop và complex reasoning.

**Trạng thái nộp bài:** Sẵn sàng, cần kiểm tra lần cuối README và đính kèm ảnh Neo4j nếu yêu cầu submission có phần minh họa graph.
