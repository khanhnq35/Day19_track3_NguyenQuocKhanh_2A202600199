import os
from typing import List, Dict, Any
from src.config import Config
from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage
from langchain.docstore.document import Document

class FlatRAG:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        Config.validate()
        self.persist_directory = persist_directory
        self.embeddings = VertexAIEmbeddings(
            model_name="text-embedding-004",
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION
        )
        self.llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )
        self.vectorstore = None

    def ingest_corpus(self, file_path: str):
        if not os.path.exists(file_path):
            print(f"❌ Không tìm thấy file: {file_path}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)
        docs = [Document(page_content=t) for t in chunks]

        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )

    def load_db(self):
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

    def query(self, question: str, k: int = 4) -> Dict[str, Any]:
        """Quy trình RAG truyền thống: Retrieve -> Answer."""
        if not self.vectorstore:
            self.load_db()

        docs = self.vectorstore.similarity_search(question, k=k)
        context = "\n\n".join([d.page_content for d in docs])

        prompt = f"""Bạn là một trợ lý AI. Hãy trả lời câu hỏi dựa trên ngữ cảnh dưới đây. 
Nếu thông tin không có trong ngữ cảnh, hãy nói rằng bạn không biết.

NGỮ CẢNH:
{context}

CÂU HỎI: {question}
TRẢ LỜI:"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return {
                "answer": response.content,
                "context": context
            }
        except Exception as e:
            return {
                "answer": f"❌ Lỗi Flat RAG: {e}",
                "context": context
            }
