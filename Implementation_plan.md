# Lab Day 19: GraphRAG Tech Company Corpus — Implementation Plan

## Tổng quan

Xây dựng hệ thống GraphRAG hoàn chỉnh: trích xuất thực thể/quan hệ từ Tech Company Corpus → lưu vào Neo4j (Docker) → truy vấn multi-hop → so sánh với Flat RAG trên 20 câu hỏi benchmark.

---

## Project Structure (Dự kiến)

```
Day19_NguyenQuocKhanh_2A202600199/
├── .venv/                          # Virtual environment
├── .env                            # API keys, Neo4j credentials
├── docker-compose.yml              # Neo4j container
├── requirements.txt                # Dependencies
├── data/
│   └── tech_company_corpus.txt     # Raw corpus (tự tạo/tổng hợp)
├── src/
│   ├── __init__.py
│   ├── config.py                   # Load .env, constants
│   ├── entity_extraction.py        # LLM-based entity/relation extraction
│   ├── graph_builder.py            # Neo4j graph construction + dedup
│   ├── graph_query.py              # Multi-hop traversal + textualization
│   ├── flat_rag.py                 # ChromaDB-based Flat RAG baseline
│   ├── graphrag_pipeline.py        # End-to-end GraphRAG pipeline
│   └── evaluation.py               # So sánh Flat RAG vs GraphRAG
├── benchmark/
│   └── questions.json              # 20 câu hỏi benchmark + ground truth
├── score_metric.md                 # Tiêu chí chấm điểm & self-validation
├── results/
│   ├── comparison_table.md         # Bảng so sánh kết quả
│   ├── cost_analysis.md            # Phân tích token usage & time
│   └── screenshots/                # Ảnh chụp Neo4j graph
├── notebooks/
│   └── lab_day19_graphrag.ipynb    # Notebook tổng hợp (optional)
└── README.md                       # Báo cáo tổng kết
```

---

## Phase 1: Research & Lý thuyết (~30 phút)

### Mục tiêu
Trả lời 3 câu hỏi nghiên cứu trong đề bài và ghi vào `README.md`.

### Tasks
- [x] **1.1** Trả lời: Entity Extraction — LLM phân biệt Node vs Attribute như thế nào?
- [x] **1.2** Trả lời: Tại sao Deduplication quan trọng?
- [x] **1.3** Trả lời: BFS graph traversal vs Vector search?

### Deliverables
- [x] `report/research.md` hoàn thành
- [x] `README.md` hoàn thành

---

## Phase 2: Environment Setup (~20 phút)

### Mục tiêu
Setup Neo4j Docker + Python virtual environment + Vertex AI credentials.

### Tasks
- [x] **2.1** Tạo `.venv` và cài dependencies
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install networkx matplotlib neo4j google-cloud-aiplatform pandas chromadb langchain langchain-google-vertexai python-dotenv
  ```
- [x] **2.2** Tạo `docker-compose.yml` cho Neo4j
- [x] **2.3** Tạo `.env` (Vertex AI config)
  ```
  GCP_PROJECT_ID=...
  GCP_LOCATION=us-central1
  GCP_MODEL_NAME=gemini-1.5-flash
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=graphrag2024
  ```
- [x] **2.4** Khởi động Neo4j, verify kết nối
- [x] **2.5** Tạo `requirements.txt` freeze và init project structure

### Deliverables
- [x] Neo4j chạy OK trên Docker
- [x] Python env sẵn sàng (Vertex AI integrated)

---

## Phase 3: Indexing Pipeline — Entity & Relation Extraction (~1.5 giờ)

### Mục tiêu
Xây dựng pipeline trích xuất thực thể/quan hệ từ corpus → đẩy vào Neo4j.

### Tasks

#### 3.1 Tạo Tech Company Corpus (`data/tech_company_corpus.txt`)
- [x] Tự động cào dữ liệu từ Wikipedia cho 26 thực thể công nghệ (OpenAI, Google, Anthropic, v.v.)
- [x] Đã thu thập ~1,300 dòng dữ liệu văn bản chất lượng.
- [x] Lưu trữ tại `data/tech_company_corpus.txt`.

#### 3.2 Entity Extraction (`src/entity_extraction.py`)
- [x] Thiết kế prompt template cho LLM extraction (Subject | Label | Relation | Object | Label)
- [x] Viết logic trích xuất sử dụng Vertex AI Gemini 1.5 Flash.
- [ ] Thực thi trích xuất (Đang chờ `GCP_PROJECT_ID` trong `.env`).

#### 3.3 Graph Construction (`src/graph_builder.py`)
- [x] Viết logic kết nối Neo4j via Bolt driver.
- [x] Viết logic tạo Constraints (Unique name cho Node labels).
- [x] Viết logic batch insert sử dụng Cypher MERGE.
- [ ] Thực thi xây dựng đồ thị (Đang chờ `data/triples.json`).

#### 3.4 Verify trên Neo4j Browser
- [x] Chạy Cypher queries kiểm tra.
- [x] Chụp screenshot → `results/screenshots/graph_viz.png`

### Deliverables
- Graph trên Neo4j với ≥50 nodes, ≥80 relationships
- Screenshots đồ thị
- Triples data có thể export

---

## Phase 4: Query Engine — Multi-hop Traversal (~1 giờ)

### Mục tiêu
Xây dựng query engine: nhận câu hỏi → extract entities → graph traversal → textualize → LLM answer.

### Tasks

#### 4.1 Graph Query (`src/graph_query.py`)
- [x] Entity extraction từ câu hỏi (dùng LLM)
- [x] Cypher-based 2-hop traversal (Undirected)
- [x] Textualization & LLM answering
- [x] Test thành công với câu hỏi multi-hop

#### 4.2 Flat RAG Baseline (`src/flat_rag.py`)
- [x] Chunk corpus → embed (text-embedding-004) → store in ChromaDB
- [x] Standard retrieval pipeline
- [x] Test thành công (và xác nhận bị giới hạn so với GraphRAG)

#### 4.3 Tạo 20 Benchmark Questions (`benchmark/questions.json`)
- [x] 10 câu single-hop (dễ, cả Flat RAG lẫn GraphRAG nên trả lời được)
- [x] 7 câu multi-hop (trung bình, GraphRAG có lợi thế)
  - VD: "CEO của công ty đã mua lại Instagram là ai?"
- [x] 3 câu complex reasoning (khó, cần traverse ≥3 hop)
  - VD: "Những sản phẩm nào sử dụng technology do công ty của Sam Altman phát triển?"
- [x] Mỗi câu kèm `ground_truth_answer`

### Deliverables
- Query engine hoạt động end-to-end
- Flat RAG baseline hoạt động
- 20 câu benchmark + ground truth

---

## Phase 5: Evaluation & Report (~1 giờ)

### Mục tiêu
Chạy benchmark, so sánh, phân tích cost, viết báo cáo.

### Tasks

#### 5.1 Evaluation (`src/evaluation.py`)
- [ ] Chạy 20 câu qua cả Flat RAG và GraphRAG
- [ ] Metrics đánh giá:
  - **Correctness**: So sánh answer vs ground_truth (LLM-as-judge hoặc exact match)
  - **Faithfulness**: Answer có dựa trên retrieved context không?
  - **Hallucination rate**: Đếm số câu bị hallucination
- [ ] Ghi nhận token usage + response time cho mỗi câu

#### 5.2 Comparison Table (`results/comparison_table.md`)
- [ ] Bảng 20 câu: Question | Ground Truth | Flat RAG Answer | GraphRAG Answer | Flat RAG Correct? | GraphRAG Correct?
- [ ] Summary statistics: accuracy, hallucination rate

#### 5.3 Cost Analysis (`results/cost_analysis.md`)
- [ ] Token usage: indexing phase (entity extraction) + query phase
- [ ] Time: indexing time + average query time
- [ ] So sánh overhead GraphRAG vs Flat RAG

#### 5.4 Final Report (`README.md`)
- [ ] Tổng kết nghiên cứu (Phase 1)
- [ ] Mô tả pipeline
- [ ] Kết quả benchmark
- [ ] Nhận xét: khi nào GraphRAG tốt hơn, khi nào không cần thiết
- [ ] Screenshots Neo4j

### Deliverables
- Bảng so sánh 20 câu
- Cost analysis
- README hoàn chỉnh
- Tất cả screenshots

---

## Timeline Tổng hợp

| Phase | Nội dung | Thời gian ước tính |
|-------|----------|-------------------|
| 1 | Research & Lý thuyết | 30 phút |
| 2 | Environment Setup (Docker, venv) | 20 phút |
| 3 | Indexing Pipeline (Extract + Neo4j) | 1.5 giờ |
| 4 | Query Engine + Benchmark | 1 giờ |
| 5 | Evaluation & Report | 1 giờ |
| **Tổng** | | **~4 giờ** |

---

## Open Questions

> [!IMPORTANT]
> 1. **Model**: Đã chuyển sang Vertex AI (Gemini 1.5 Flash).
> 2. **Corpus**: Cần tự tạo trong Phase 3.
> 3. **NodeRAG**: Tạm thời chỉ focus Neo4j để tối ưu logic.
> 4. **Notebook vs Script**: Ưu tiên `.py` scripts để dễ maintain.

---

## Verification Plan

### Automated
```bash
# Verify Neo4j connection
python -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j','graphrag2024')); d.verify_connectivity()"

# Run score_metric validation
python -m src.evaluation --validate
```

### Manual
- Kiểm tra Neo4j Browser tại `http://localhost:7474`
- Review bảng so sánh 20 câu
- Chạy `score_metric.md` checklist trước khi nộp
