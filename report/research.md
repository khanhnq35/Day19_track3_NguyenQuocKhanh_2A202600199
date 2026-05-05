# Research: GraphRAG Fundamentals

Tài liệu này tổng hợp kết quả nghiên cứu về các khái niệm cốt lõi trong xây dựng hệ thống GraphRAG, tập trung vào trích xuất tri thức, quản lý dữ liệu đồ thị và cơ chế truy vấn.

---

## 1. Entity Extraction: Node vs Attribute

**Câu hỏi:** Làm sao để LLM phân biệt được đâu là thực thể (Node) và đâu là thuộc tính (Attribute)?

**Trả lời:**
Việc phân biệt dựa trên **Prompt Engineering** và **Schema Definition**:
- **Schema Definition:** Chúng ta cung cấp cho LLM một danh mục các loại thực thể (ví dụ: `COMPANY`, `PERSON`) và các loại quan hệ (`CEO_OF`, `FOUNDED_BY`).
- **Prompt Engineering:** Sử dụng kỹ thuật *Few-shot prompting* để hướng dẫn LLM. 
    - **Node (Thực thể):** Là các đối tượng có định danh riêng, có thể tồn tại độc lập và có các mối quan hệ với đối tượng khác. Ví dụ: "OpenAI" là một thực thể loại `COMPANY`.
    - **Attribute (Thuộc tính):** Là các thông tin mô tả đặc điểm của Node nhưng không nhất thiết phải là một Node riêng biệt trong đồ thị (trừ khi cần phân tích sâu). Ví dụ: "Năm thành lập: 2015" thường là thuộc tính của Node "OpenAI", nhưng trong GraphRAG, "2015" cũng có thể được coi là một Node loại `YEAR` để liên kết các sự kiện xảy ra cùng năm.
- **Quy tắc trích xuất:** Nếu thông tin đó đóng vai trò là "chủ ngữ" hoặc "vị ngữ" trong một câu khẳng định về mối quan hệ, nó là Node. Nếu nó chỉ là thông tin bổ trợ trong cấu trúc JSON của Node, nó là Attribute.

---

## 2. Graph Construction: Tầm quan trọng của Deduplication

**Câu hỏi:** Tại sao việc khử trùng lặp (Deduplication) lại quan trọng trong đồ thị?

**Trả lời:**
Deduplication (Khử trùng lặp thực thể - Entity Resolution) là bước sống còn vì:
- **Tính toàn vẹn của tri thức:** Nếu "OpenAI", "Open AI" và "openai" được lưu thành 3 node khác nhau, đồ thị sẽ bị phân mảnh. Các quan hệ liên quan đến cùng một thực thể sẽ không hội tụ về một điểm, làm mất đi khả năng kết nối tri thức.
- **Độ chính xác của Multi-hop Query:** Truy vấn GraphRAG dựa trên việc "nhảy" (hop) giữa các node. Nếu node bị trùng lặp, đường đi (path) sẽ bị đứt gãy. Ví dụ: Để tìm "CEO của công ty do Elon Musk sáng lập", ta cần đi từ `Elon Musk` -> `OpenAI` -> `CEO`. Nếu node `OpenAI` bị tách làm hai, truy vấn sẽ không tìm thấy đích.
- **Tiết kiệm tài nguyên:** Giảm số lượng node và quan hệ rác, giúp việc duyệt đồ thị nhanh hơn và LLM context ngắn gọn hơn.

---

## 3. Query Answering: BFS Traversal vs Vector Search

**Câu hỏi:** Sự khác biệt giữa duyệt đồ thị theo chiều rộng (BFS) và tìm kiếm vector thông thường là gì?

**Trả lời:**

| Đặc điểm | Vector Search (Flat RAG) | BFS Traversal (GraphRAG) |
|----------|--------------------------|--------------------------|
| **Cơ chế** | So sánh độ tương đồng cosine giữa vector truy vấn và vector chunk. | Xuất phát từ node gốc và duyệt qua các quan hệ lân cận (multi-hop). |
| **Phạm vi** | Chỉ tìm các đoạn văn có từ ngữ/ngữ nghĩa tương đồng cục bộ. | Tìm được các mối liên hệ gián tiếp mà văn bản gốc không viết cạnh nhau. |
| **Thế mạnh** | Trả lời tốt câu hỏi "Cái gì?", "Ở đâu?" (Single-fact). | Trả lời tốt câu hỏi "Tại sao?", "Mối quan hệ như thế nào?" (Complex/Multi-step reasoning). |
| **Hạn chế** | Dễ bị Hallucination khi thông tin nằm rải rác ở nhiều trang/tài liệu. | Đòi hỏi chi phí trích xuất đồ thị (Indexing) cao hơn và logic phức tạp hơn. |

**Kết luận:** BFS Traversal cho phép hệ thống "suy luận" dựa trên cấu trúc liên kết, giúp thu thập context chính xác hơn cho các câu hỏi phức tạp mà Vector Search thường bỏ lỡ.
