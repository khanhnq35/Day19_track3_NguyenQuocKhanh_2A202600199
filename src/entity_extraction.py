import os
import json
import re
from typing import List, Dict
from src.config import Config
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage

class EntityExtractor:
    def __init__(self):
        Config.validate()
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )
        self.system_instruction = """Bạn là một chuyên gia về Knowledge Graph. 
Nhiệm vụ của bạn là trích xuất các thực thể (Nodes) và quan hệ (Relations) từ văn bản dưới dạng bộ ba (Triples): (Subject, Subject_Label, Relation, Object, Object_Label).

Sử dụng các loại Node sau: COMPANY, PERSON, PRODUCT, TECHNOLOGY, YEAR, LOCATION.
Sử dụng các loại Relation sau: FOUNDED_BY, CEO_OF, DEVELOPED, ACQUIRED, INVESTED_IN, PARTNER_WITH, HEADQUARTERED_IN, FOUNDED_IN, USES_TECHNOLOGY, EMPLOYED_BY, CO_FOUNDED.

Quy tắc:
1. Mỗi dòng trả về một bộ ba theo định dạng: Subject | Subject_Label | Relation | Object | Object_Label
2. Subject_Label và Object_Label phải nằm trong danh sách Node types cho trước.
3. Relation phải nằm trong danh sách Relation types cho trước.
4. Trích xuất tối đa các mối quan hệ quan trọng, đặc biệt là thông tin về người sáng lập và nhân viên cũ.
5. Chỉ trả về các triples, không giải thích gì thêm."""

    def extract_triples(self, text: str) -> List[Dict[str, str]]:
        """Trích xuất triples từ một đoạn văn bản sử dụng HumanMessage trực tiếp."""
        try:
            # Sử dụng danh sách tin nhắn đơn giản để tránh lỗi 400 của Vertex AI
            prompt_text = f"{self.system_instruction}\n\nTrích xuất tri thức từ văn bản sau:\n\n{text}"
            message = HumanMessage(content=prompt_text)
            
            response = self.llm.invoke([message])
            content = response.content
            
            lines = content.strip().split("\n")
            triples = []
            for line in lines:
                parts = line.split("|")
                if len(parts) == 5:
                    triples.append({
                        "subject": parts[0].strip(),
                        "subject_label": parts[1].strip().upper(),
                        "relation": parts[2].strip().upper(),
                        "object": parts[3].strip(),
                        "object_label": parts[4].strip().upper()
                    })
            return triples
        except Exception as e:
            print(f"❌ Lỗi trích xuất: {e}")
            return []

    def process_corpus(self, input_file: str, output_file: str):
        """Xử lý toàn bộ corpus và lưu triples."""
        if not os.path.exists(input_file):
            print(f"❌ Không tìm thấy file corpus: {input_file}")
            return

        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Chia nhỏ theo dấu ngăn cách bài viết
        articles = content.split("="*50)
        all_triples = []

        # Lọc bỏ các bài viết trống
        valid_articles = [a.strip() for a in articles if len(a.strip()) > 100]

        print(f"🔄 Bắt đầu trích xuất từ {len(valid_articles)} bài viết...")
        for i, article in enumerate(valid_articles):
            print(f"📝 Đang xử lý bài {i+1}/{len(valid_articles)}...")
            # Lấy 3000 ký tự đầu của mỗi bài
            text_to_process = article[:3000] 
            triples = self.extract_triples(text_to_process)
            all_triples.extend(triples)

        # Deduplication cơ bản
        unique_triples = []
        seen = set()
        for t in all_triples:
            key = (t["subject"].lower(), t["relation"].upper(), t["object"].lower())
            if key not in seen:
                seen.add(key)
                unique_triples.append(t)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_triples, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Đã trích xuất xong {len(unique_triples)} triples. Lưu tại: {output_file}")

if __name__ == "__main__":
    extractor = EntityExtractor()
    extractor.process_corpus("data/tech_company_corpus.txt", "data/triples.json")
