# Cost and Performance Analysis (Template)

## 1. Summary Comparison Table

| Chỉ số (Indicator) | Flat RAG | Graph RAG | Delta (Overhead/Improvement) |
|---|---|---|---|
| **Accuracy (Avg)** | {{avg_flat_score}} | {{avg_graph_score}} | {{score_delta}} |
| **Response Time (Avg)** | {{avg_flat_time}}s | {{avg_graph_time}}s | {{time_delta}}% |
| **Token Usage (Est. Indexing)** | ~400 chunks | ~600 triples | N/A |
| **Latency (P95)** | {{p95_flat_time}}s | {{p95_graph_time}}s | {{p95_delta}}s |
| **Context Size (Avg chars)** | ~4000 chars | ~1500 chars | {{context_delta}}% |

---

## 2. Detailed Performance Indicators

### 2.1. Retrieval Efficiency
- **Flat RAG**: Sử dụng ChromaDB + Vector Search. Hiệu quả cao với các câu hỏi Keyword/Semantic.
- **GraphRAG**: Sử dụng Neo4j + Cypher 2-hop. Hiệu quả trong việc kết nối các thực thể rời rạc nhưng tốn thêm bước "Extract Entity" (LLM call).

### 2.2. Cost Analysis (Token & LLM Calls)
- **Indexing Phase**:
  - Flat RAG: Tốn token cho Embedding (text-embedding-004).
  - GraphRAG: Tốn token cho LLM Extraction (Gemini 2.5 Flash) - **Đây là chi phí lớn nhất**.
- **Query Phase**:
  - Flat RAG: 1 LLM call (Answer).
  - GraphRAG: 2 LLM calls (Extract Entities + Answer).

### 2.3. Complexity & Scalability
- **Flat RAG**: Dễ mở rộng, chỉ cần thêm document.
- **GraphRAG**: Phức tạp hơn trong việc duy trì schema và đảm bảo chất lượng triple trích xuất.

## 3. Conclusion & Recommendations
[Phần này sẽ tự động sinh dựa trên kết quả chạy thực tế]
