import json
import os
import time
import re
import numpy as np
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import Config
from src.graph_query import GraphQueryEngine
from src.flat_rag import FlatRAG
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

class Evaluator:
    def __init__(self):
        Config.validate()
        # Lưu ý: Thread-safe? Neo4j driver và Langchain LLM thường thread-safe.
        self.graph_engine = GraphQueryEngine()
        self.flat_engine = FlatRAG()
        self.judge_llm = ChatVertexAI(
            model_name=Config.GCP_MODEL_NAME,
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_LOCATION,
            temperature=0,
        )
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)

    def get_judge_score(self, prompt: str) -> float:
        try:
            response = self.judge_llm.invoke([HumanMessage(content=prompt)])
            score_str = response.content.strip()
            match = re.search(r"([0-9]\.[0-9]|[0-1])", score_str)
            return float(match.group(1)) if match else 0.0
        except Exception:
            return 0.0

    def evaluate_all_metrics(self, question: str, ground_truth: str, answer: str, context: str) -> Dict[str, float]:
        correctness_prompt = f"CORRECTNESS (0.0-1.0).\nQ: {question}\nGT: {ground_truth}\nA: {answer}\nScore:"
        faithfulness_prompt = f"FAITHFULNESS (0.0-1.0).\nCtx: {context}\nA: {answer}\nScore:"
        hallucination_prompt = f"NO-HALLUCINATION (0.0-1.0).\nCtx: {context}\nA: {answer}\nScore (1.0=No hallu):"

        return {
            "correctness": self.get_judge_score(correctness_prompt),
            "faithfulness": self.get_judge_score(faithfulness_prompt),
            "no_hallucination": self.get_judge_score(hallucination_prompt)
        }

    def process_single_question(self, q: Dict) -> Dict:
        # GraphRAG
        start_t = time.time()
        g_res = self.graph_engine.query(q['question'])
        g_time = time.time() - start_t
        g_metrics = self.evaluate_all_metrics(q['question'], q['ground_truth'], g_res["answer"], g_res["context"])
        
        # Flat RAG
        start_t = time.time()
        f_res = self.flat_engine.query(q['question'])
        f_time = time.time() - start_t
        f_metrics = self.evaluate_all_metrics(q['question'], q['ground_truth'], f_res["answer"], f_res["context"])

        return {
            "id": q["id"], "category": q["category"], "question": q["question"], "ground_truth": q["ground_truth"],
            "graph_rag": {"answer": g_res["answer"], "metrics": g_metrics, "time": g_time, "context_len": len(g_res["context"])},
            "flat_rag": {"answer": f_res["answer"], "metrics": f_metrics, "time": f_time, "context_len": len(f_res["context"])}
        }

    def run_benchmark(self, questions_path: str):
        with open(questions_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        print(f"🚀 Chạy benchmark (4 luồng song song) cho {len(questions)} câu hỏi...")
        evaluation_data = []

        # ChromaDB Rust client không ổn định khi 4 luồng cùng gọi load_db().
        # Load vectorstore một lần ở main thread trước, sau đó các worker chỉ đọc.
        if not self.flat_engine.vectorstore:
            print("📦 Preload Flat RAG vectorstore...")
            self.flat_engine.load_db()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_q = {executor.submit(self.process_single_question, q): q for q in questions}
            for future in as_completed(future_to_q):
                res = future.result()
                evaluation_data.append(res)
                print(f"✅ Xong câu {res['id']}")

        # Sắp xếp lại theo ID
        evaluation_data.sort(key=lambda x: x["id"])

        with open(os.path.join(self.results_dir, "eval_results.json"), "w", encoding="utf-8") as f:
            json.dump(evaluation_data, f, indent=4, ensure_ascii=False)
        
        self.generate_reports(evaluation_data)

    def generate_reports(self, data: List[Dict]):
        # Report 1: comparison_table.md
        table_md = "# Evaluation Comparison Table\n\n| ID | Category | Question | Flat RAG (C/F/H) | GraphRAG (C/F/H) | Win |\n|---|---|---|---|---|---|\n"
        stats = {cat: {"graph": [], "flat": []} for cat in ["single-hop", "multi-hop", "complex-reasoning"]}

        for r in data:
            f_m, g_m = r["flat_rag"]["metrics"], r["graph_rag"]["metrics"]
            f_str = f"{f_m['correctness']}/{f_m['faithfulness']}/{f_m['no_hallucination']}"
            g_str = f"{g_m['correctness']}/{g_m['faithfulness']}/{g_m['no_hallucination']}"
            winner = "Graph" if g_m["correctness"] > f_m["correctness"] else ("Flat" if f_m["correctness"] > g_m["correctness"] else "Draw")
            table_md += f"| {r['id']} | {r['category']} | {r['question']} | {f_str} | {g_str} | {winner} |\n"
            stats[r["category"]]["graph"].append(g_m["correctness"])
            stats[r["category"]]["flat"].append(f_m["correctness"])

        table_md += "\n## Summary Statistics (Accuracy)\n\n| Category | Flat RAG Avg | GraphRAG Avg | Delta (G-F) |\n|---|---|---|---|\n"
        for cat, scores in stats.items():
            avg_f, avg_g = np.mean(scores["flat"]), np.mean(scores["graph"])
            table_md += f"| {cat} | {avg_f:.2f} | {avg_g:.2f} | {avg_g - avg_f:+.2f} |\n"
        
        with open("results/comparison_table.md", "w", encoding="utf-8") as f: f.write(table_md)

        # Report 2: cost_analysis.md
        f_times, g_times = [r["flat_rag"]["time"] for r in data], [r["graph_rag"]["time"] for r in data]
        f_ctx, g_ctx = [r["flat_rag"]["context_len"] for r in data], [r["graph_rag"]["context_len"] for r in data]
        f_c = [r["flat_rag"]["metrics"]["correctness"] for r in data]
        g_c = [r["graph_rag"]["metrics"]["correctness"] for r in data]

        cost_md = f"""# Cost and Performance Analysis

| Chỉ số (Indicator) | Flat RAG | Graph RAG | Delta (G-F) |
|---|---|---|---|
| **Accuracy (Avg)** | {np.mean(f_c):.2f} | {np.mean(g_c):.2f} | {np.mean(g_c)-np.mean(f_c):+.2f} |
| **Response Time (Avg)** | {np.mean(f_times):.2f}s | {np.mean(g_times):.2f}s | {np.mean(g_times)-np.mean(f_times):+.2f}s |
| **Latency (P95)** | {np.percentile(f_times, 95):.2f}s | {np.percentile(g_times, 95):.2f}s | {np.percentile(g_times, 95)-np.percentile(f_times, 95):+.2f}s |
| **Context Size (Avg chars)** | {int(np.mean(f_ctx))} | {int(np.mean(g_ctx))} | {int(np.mean(g_ctx)-np.mean(f_ctx)):+d} |
| **Faithfulness (Avg)** | {np.mean([r['flat_rag']['metrics']['faithfulness'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['faithfulness'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['faithfulness'] for r in data])-np.mean([r['flat_rag']['metrics']['faithfulness'] for r in data]):+.2f} |
| **No-Hallucination (Avg)** | {np.mean([r['flat_rag']['metrics']['no_hallucination'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['no_hallucination'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['no_hallucination'] for r in data])-np.mean([r['flat_rag']['metrics']['no_hallucination'] for r in data]):+.2f} |
"""
        with open("results/cost_analysis.md", "w", encoding="utf-8") as f: f.write(cost_md)
        print("✅ Reports updated.")

if __name__ == "__main__":
    Evaluator().run_benchmark("benchmark/questions.json")
