import os
from typing import List, Dict, Any
from neo4j import GraphDatabase
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
from src.config import Config

class GraphQueryEngine:
    def __init__(self):
        Config.validate()
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        )
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )

    def close(self):
        self.driver.close()

    def extract_entities(self, question: str) -> List[str]:
        """Sử dụng LLM để trích xuất thực thể."""
        prompt = f"""Trích xuất tên các thực thể chính (Công ty, Người, Sản phẩm) từ câu hỏi.
Trả về danh sách phân cách bởi dấu phẩy. Trả về 'None' nếu không có.

Câu hỏi: {question}
Thực thể:"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            entities = [e.strip() for e in response.content.split(",") if e.strip() != "None"]
            return entities
        except Exception:
            return []

    def get_graph_context(self, entities: List[str]) -> str:
        """Truy vấn thông minh: Kết hợp 2-hop local và Path-finding giữa các thực thể."""
        if not entities:
            return ""
            
        context_parts = []
        with self.driver.session() as session:
            # 1. Tìm đường đi giữa các thực thể (Dành cho Multi-hop/Complex Reasoning)
            if len(entities) >= 2:
                path_query = """
                MATCH (n1), (n2)
                WHERE n1.name =~ ('(?i)' + $e1) AND n2.name =~ ('(?i)' + $e2) AND n1 <> n2
                MATCH p = shortestPath((n1)-[*..3]-(n2))
                RETURN p
                """
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        res = session.run(path_query, e1=entities[i], e2=entities[j])
                        for record in res:
                            path = record["p"]
                            path_str = " -> ".join([node["name"] for node in path.nodes])
                            rels = [type(r) for r in path.relationships]
                            context_parts.append(f"Đường đi: {path_str} thông qua các quan hệ {rels}")

            # 2. Local context (2-hop) cho từng thực thể
            local_query = """
            MATCH (n) WHERE n.name =~ ('(?i)' + $name)
            MATCH (n)-[r1]-(m)
            OPTIONAL MATCH (m)-[r2]-(k)
            RETURN n.name as s, type(r1) as r1, m.name as m, type(r2) as r2, k.name as e
            LIMIT 50
            """
            for entity in entities:
                res = session.run(local_query, name=entity)
                for record in res:
                    line = f"{record['s']} {record['r1']} {record['m']}"
                    if record['r2'] and record['e']:
                        line += f", và {record['m']} {record['r2']} {record['e']}"
                    context_parts.append(line)
        
        return "\n".join(list(set(context_parts)))

    def query(self, question: str) -> Dict[str, Any]:
        """Quy trình GraphRAG tối ưu."""
        entities = self.extract_entities(question)
        graph_context = self.get_graph_context(entities)
        
        if not graph_context:
            return {"answer": "Tôi không tìm thấy dữ liệu liên quan trong đồ thị.", "context": "", "entities": entities}

        prompt = f"""Bạn là chuyên gia phân tích dữ liệu đồ thị. Hãy trả lời câu hỏi dựa trên các mối quan hệ dưới đây.
Nếu ngữ cảnh có 'Đường đi', đó là chuỗi logic quan trọng cho Multi-hop.

NGỮ CẢNH ĐỒ THỊ:
{graph_context}

CÂU HỎI: {question}
TRẢ LỜI:"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return {"answer": response.content, "context": graph_context, "entities": entities}
        except Exception as e:
            return {"answer": f"Lỗi: {e}", "context": graph_context, "entities": entities}
