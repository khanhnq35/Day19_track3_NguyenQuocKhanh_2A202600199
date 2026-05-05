import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # GCP Vertex AI
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
    GCP_MODEL_NAME = os.getenv("GCP_MODEL_NAME", "gemini-1.5-flash")
    
    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "graphrag2024")
    
    # Paths
    DATA_PATH = "data/tech_company_corpus.txt"
    BENCHMARK_PATH = "benchmark/questions.json"
    
    @classmethod
    def validate(cls):
        """Check if essential configs are set."""
        if not cls.GCP_PROJECT_ID:
            print("⚠️ WARNING: GCP_PROJECT_ID is not set in .env")
        print(f"✅ Config loaded for Project: {cls.GCP_PROJECT_ID}, Model: {cls.GCP_MODEL_NAME}")

if __name__ == "__main__":
    Config.validate()
