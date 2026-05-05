# Implementation Report: GraphRAG for Tech Company Corpus

Báo cáo này mô tả chi tiết logic triển khai và kết quả thực hiện hệ thống GraphRAG kể từ Phase 3.

---

## 1. Phase 3: Indexing Pipeline (Hoàn thành 100%)

Giai đoạn này đã chuyển đổi thành công 26 bài báo Wikipedia thành một đồ thị tri thức tập trung.

### 1.1. Data Fetching
- Thu thập sạch dữ liệu cho **26 chủ đề** công nghệ. Lưu tại `data/tech_company_corpus.txt`.

### 1.2. Entity & Relation Extraction
- Sử dụng **Gemini 2.5 Flash** trích xuất **594 triples** tri thức.

### 1.3. Graph Construction
- Xây dựng thành công đồ thị Neo4j với **487 Nodes** và **594 Relationships**.

---

## 2. Phase 4: Query Engine (Hoàn thành 80%)

Giai đoạn này tập trung vào việc hiện thực hóa khả năng truy vấn và đối chứng hiệu quả.

### 2.1. GraphRAG Engine (Task 4.1)
- **Logic:** Tự động trích xuất thực thể từ câu hỏi -> Truy vấn không hướng (undirected) 2-hop trên Neo4j -> Tổng hợp ngữ cảnh -> LLM trả lời.
- **Kết quả:** Trả lời chính xác các câu hỏi phức tạp đòi hỏi kết nối thông tin giữa các bài báo khác nhau.

### 2.2. Flat RAG Baseline (Task 4.2)
- **Logic:** Sử dụng ChromaDB làm VectorStore, nhúng văn bản bằng `text-embedding-004`.
- **Kết quả:** Hoạt động tốt với câu hỏi trực tiếp nhưng gặp hạn chế lớn với các câu hỏi liên quan đến nhân sự hoặc quan hệ đối tác nếu thông tin nằm ở các đoạn văn bản cách xa nhau.

### 2.3. Đối chứng thực tế (Case Study)
**Câu hỏi:** *"Ai là CEO của công ty đã phát triển ChatGPT?"*
- **GraphRAG:** Trả lời đúng **Sam Altman** (nhờ nối `ChatGPT` -> `OpenAI` -> `CEO`).
- **Flat RAG:** Chỉ biết công ty là **OpenAI**, không tìm thấy thông tin CEO trong các đoạn văn bản được truy xuất (Top-k).

---

## 3. Trạng thái hiện tại

| Bước | Trạng thái | Ghi chú |
|------|------------|---------|
| Indexing Pipeline | ✅ Hoàn thành | 487 Nodes, 594 Rel |
| GraphRAG Engine | ✅ Hoàn thành | Hỗ trợ Multi-hop traversal |
| Flat RAG Baseline | ✅ Hoàn thành | Đã ingest 405 chunks vào ChromaDB |
| Benchmark Setup | 🔄 Đang hoàn tất | Đang sinh bộ 20 câu hỏi đánh giá |
| Evaluation | ⏳ Chờ đợi | Sẽ thực hiện sau khi có Benchmark |

---
**Cập nhật lần cuối:** 05/05/2026
**Người thực hiện:** Nguyễn Quốc Khánh
