import json
import os
from src.config import Config
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

def generate_questions():
    Config.validate()
    llm = ChatVertexAI(
        model_name=Config.GCP_MODEL_NAME,
        project=Config.GCP_PROJECT_ID,
        location=Config.GCP_LOCATION,
        temperature=0.7, # Tăng temperature để đa dạng câu hỏi
    )

    # Đọc một phần corpus để làm ngữ cảnh sinh câu hỏi
    with open("data/tech_company_corpus.txt", "r", encoding="utf-8") as f:
        corpus_sample = f.read()[:5000]

    prompt = f"""Dựa trên thông tin về các công ty công nghệ dưới đây, hãy tạo ra 20 câu hỏi đánh giá (benchmark) theo đúng định dạng JSON.

Yêu cầu bộ câu hỏi:
1. 10 câu Single-hop: Câu hỏi trực tiếp về 1 thực thể (VD: AI của Google tên là gì?).
2. 7 câu Multi-hop: Câu hỏi đòi hỏi kết nối 2 thực thể qua 1 thực thể trung gian (VD: CEO của công ty đầu tư vào OpenAI là ai?).
3. 3 câu Complex Reasoning: Câu hỏi đòi hỏi suy luận từ nhiều mối quan hệ (VD: Những người sáng lập Alphabet hiện đang giữ chức vụ gì?).

Định dạng JSON trả về:
[
  {{
    "id": 1,
    "category": "single-hop",
    "question": "...",
    "ground_truth": "..."
  }},
  ...
]

Dữ liệu tham khảo:
{corpus_sample}
"""

    print("🧠 Đang sinh bộ câu hỏi benchmark...")
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    
    # Làm sạch kết quả JSON nếu LLM trả về kèm markdown
    json_str = re.search(r"\[.*\]", content, re.DOTALL).group(0)
    questions = json.loads(json_str)

    os.makedirs("benchmark", exist_ok=True)
    with open("benchmark/questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Đã tạo xong {len(questions)} câu hỏi tại benchmark/questions.json")

if __name__ == "__main__":
    import re
    generate_questions()
