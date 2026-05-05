# Cost and Performance Analysis

| Chỉ số (Indicator) | Flat RAG | Graph RAG | Delta (G-F) |
|---|---|---|---|
| **Accuracy (Avg)** | 0.80 | 0.43 | -0.37 |
| **Response Time (Avg)** | 3.40s | 6.20s | +2.81s |
| **Latency (P95)** | 4.99s | 8.93s | +3.94s |
| **Context Size (Avg chars)** | 2826 | 7336 | +4510 |
| **Faithfulness (Avg)** | 0.94 | 0.95 | +0.01 |
| **No-Hallucination (Avg)** | 1.00 | 0.88 | -0.12 |

---

## Conclusion
Báo cáo cho thấy GraphRAG có xu hướng tốn thời gian hơn (do 2 LLM calls) nhưng cung cấp ngữ cảnh cô đọng hơn. Độ chính xác và Delta sẽ được phân tích sâu hơn trong README.
