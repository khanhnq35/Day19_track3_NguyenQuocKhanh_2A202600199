import json
from neo4j import GraphDatabase
from src.config import Config

class GraphBuilder:
    def __init__(self):
        Config.validate()
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def create_constraints(self):
        """Tạo các ràng buộc Unique để tránh trùng lặp Node."""
        labels = ["COMPANY", "PERSON", "PRODUCT", "TECHNOLOGY", "YEAR", "LOCATION"]
        with self.driver.session() as session:
            for label in labels:
                try:
                    session.run(f"CREATE CONSTRAINT {label}_name IF NOT EXISTS FOR (n:{label}) REQUIRE n.name IS UNIQUE")
                    print(f"✅ Created constraint for {label}")
                except Exception as e:
                    print(f"⚠️ Error creating constraint for {label}: {e}")

    def build_graph(self, triples_file: str):
        """Đọc triples từ file JSON và đẩy vào Neo4j."""
        with open(triples_file, "r", encoding="utf-8") as f:
            triples = json.load(f)

        print(f"🏗️ Bắt đầu xây dựng đồ thị từ {len(triples)} triples...")
        
        with self.driver.session() as session:
            for t in triples:
                # MERGE Subject Node
                # MERGE Object Node
                # MERGE Relationship
                query = f"""
                MERGE (s:{t['subject_label']} {{name: $subject}})
                MERGE (o:{t['object_label']} {{name: $object}})
                MERGE (s)-[r:{t['relation']}]->(o)
                """
                try:
                    session.run(query, subject=t['subject'], object=t['object'])
                except Exception as e:
                    print(f"❌ Lỗi khi thực thi Cypher cho triple {t}: {e}")

        print("✅ Xây dựng đồ thị hoàn tất!")

    def verify_graph(self):
        """Kiểm tra số lượng node và quan hệ."""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            print(f"📊 Thống kê đồ thị: {node_count} Nodes, {rel_count} Relationships.")

if __name__ == "__main__":
    builder = GraphBuilder()
    builder.create_constraints()
    builder.build_graph("data/triples.json")
    builder.verify_graph()
    builder.close()
