# GraphRAG: Tech Company Corpus Analysis

Dự án này triển khai hệ thống **GraphRAG** (Graph Retrieval-Augmented Generation) để phân tích và truy vấn thông tin từ bộ dữ liệu về các công ty công nghệ (Tech Company Corpus). Hệ thống sử dụng Neo4j làm cơ sở dữ liệu đồ thị và OpenAI LLM để trích xuất tri thức và trả lời câu hỏi.

---

## 🚀 Tính năng chính

- **Entity & Relation Extraction:** Tự động trích xuất thực thể (Công ty, Con người, Sản phẩm...) và mối quan hệ từ văn bản thô bằng LLM.
- **Knowledge Graph Storage:** Lưu trữ tri thức dưới dạng đồ thị trong **Neo4j** (chạy qua Docker).
- **Multi-hop Querying:** Khả năng truy vấn liên kết phức tạp (ví dụ: Tìm CEO của công ty đối tác của X).
- **Benchmark & Evaluation:** So sánh hiệu suất giữa **Flat RAG** (Vector Search) và **GraphRAG** trên 20 câu hỏi thử nghiệm.

---

## 🛠️ Công nghệ sử dụng

- **Database:** Neo4j (5-community)
- **Frameworks:** LangChain, OpenAI API
- **Vector DB:** ChromaDB (cho baseline Flat RAG)
- **Infrastructure:** Docker, Python 3.10+

---

## 📁 Cấu trúc dự án

- `src/`: Mã nguồn chính (Extraction, Builder, Query, Evaluation).
- `data/`: Dữ liệu văn bản thô về các tập đoàn công nghệ.
- `report/`: Các báo cáo nghiên cứu và kết quả thực nghiệm.
- `benchmark/`: Bộ câu hỏi và đáp án chuẩn để đánh giá.
- `docker-compose.yml`: Cấu hình chạy Neo4j.

---

## 📖 Hướng dẫn nhanh

1. **Cài đặt môi trường:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Chạy Neo4j:**
   ```bash
   docker-compose up -d
   ```

3. **Thiết lập API Key:**
   Copy `.env.example` thành `.env` và điền `OPENAI_API_KEY`.

4. **Nghiên cứu lý thuyết:** Xem chi tiết tại [report/research.md](report/research.md).

---

## 📊 Kết quả đánh giá
*(Sẽ được cập nhật sau khi hoàn thành Phase 5)*

---
**Tác giả:** Nguyễn Quốc Khánh - 2A202600199
**Ngày thực hiện:** 05/05/2026
