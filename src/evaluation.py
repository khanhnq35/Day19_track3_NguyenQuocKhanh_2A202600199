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
from src.hybrid_rag import HybridRAG
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

class Evaluator:
    def __init__(self):
        Config.validate()
        # Lưu ý: Thread-safe? Neo4j driver và Langchain LLM thường thread-safe.
        self.graph_engine = GraphQueryEngine()
        self.flat_engine = FlatRAG()
        self.hybrid_engine = HybridRAG()
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

        # Hybrid RAG
        start_t = time.time()
        h_res = self.hybrid_engine.query(q['question'])
        h_time = time.time() - start_t
        h_context = h_res.get("merged_context", "")
        h_metrics = self.evaluate_all_metrics(q['question'], q['ground_truth'], h_res["answer"], h_context)

        return {
            "id": q["id"], "category": q["category"], "question": q["question"], "ground_truth": q["ground_truth"],
            "graph_rag": {"answer": g_res["answer"], "metrics": g_metrics, "time": g_time, "context_len": len(g_res["context"])},
            "flat_rag": {"answer": f_res["answer"], "metrics": f_metrics, "time": f_time, "context_len": len(f_res["context"])},
            "hybrid_rag": {"answer": h_res["answer"], "metrics": h_metrics, "time": h_time, "context_len": len(h_context)},
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
        def _escape_md(value: object) -> str:
            """Escape Markdown table-breaking characters."""
            return str(value).replace("|", "\\|").replace("\n", " ")

        def _metric_str(metrics: Dict[str, float]) -> str:
            """Format correctness/faithfulness/no-hallucination scores."""
            return (
                f"{metrics['correctness']:.2f}/"
                f"{metrics['faithfulness']:.2f}/"
                f"{metrics['no_hallucination']:.2f}"
            )

        def _accuracy(rows: List[Dict], rag_key: str) -> float:
            """Calculate average correctness for one RAG pipeline."""
            return float(np.mean([r[rag_key]["metrics"]["correctness"] for r in rows]))

        def _best_pipeline(scores: Dict[str, float]) -> str:
            """Return best pipeline name or Draw for tied correctness."""
            best_score = max(scores.values())
            winners = [name for name, score in scores.items() if score == best_score]
            return "Draw" if len(winners) > 1 else winners[0]

        # Report 1: comparison_table.md
        category_order = ["single-hop", "multi-hop", "complex-reasoning"]
        category_titles = {
            "single-hop": "Single-hop Questions",
            "multi-hop": "Multi-hop Questions",
            "complex-reasoning": "Complex Reasoning Questions",
        }
        grouped_data = {cat: [] for cat in category_order}
        for row in data:
            grouped_data.setdefault(row["category"], []).append(row)

        table_lines = [
            "# Evaluation Comparison Table",
            "",
            "> Metric format: `Correctness / Faithfulness / No-Hallucination`.",
            "",
            "## Overall Summary",
            "",
            "| Category | # Questions | Flat RAG Acc | GraphRAG Acc | HybridRAG Acc | Best System |",
            "|---|---:|---:|---:|---:|---|",
        ]

        for category in category_order:
            rows = grouped_data.get(category, [])
            if not rows:
                continue
            flat_acc = _accuracy(rows, "flat_rag")
            graph_acc = _accuracy(rows, "graph_rag")
            hybrid_acc = _accuracy(rows, "hybrid_rag")
            best_system = _best_pipeline(
                {"Flat": flat_acc, "Graph": graph_acc, "Hybrid": hybrid_acc}
            )
            table_lines.append(
                f"| {category} | {len(rows)} | {flat_acc:.2f} | {graph_acc:.2f} | "
                f"{hybrid_acc:.2f} | {best_system} |"
            )

        all_flat = _accuracy(data, "flat_rag")
        all_graph = _accuracy(data, "graph_rag")
        all_hybrid = _accuracy(data, "hybrid_rag")
        overall_best = _best_pipeline(
            {"Flat": all_flat, "Graph": all_graph, "Hybrid": all_hybrid}
        )
        table_lines.append(
            f"| **Overall** | **{len(data)}** | **{all_flat:.2f}** | "
            f"**{all_graph:.2f}** | **{all_hybrid:.2f}** | **{overall_best}** |"
        )

        for category in category_order:
            rows = grouped_data.get(category, [])
            if not rows:
                continue
            table_lines.extend(
                [
                    "",
                    f"## {category_titles[category]}",
                    "",
                    "| ID | Question | Flat RAG | GraphRAG | HybridRAG | Best |",
                    "|---:|---|---:|---:|---:|---|",
                ]
            )
            for row in rows:
                scores = {
                    "Flat": row["flat_rag"]["metrics"]["correctness"],
                    "Graph": row["graph_rag"]["metrics"]["correctness"],
                    "Hybrid": row["hybrid_rag"]["metrics"]["correctness"],
                }
                table_lines.append(
                    f"| {row['id']} | {_escape_md(row['question'])} | "
                    f"{_metric_str(row['flat_rag']['metrics'])} | "
                    f"{_metric_str(row['graph_rag']['metrics'])} | "
                    f"{_metric_str(row['hybrid_rag']['metrics'])} | "
                    f"{_best_pipeline(scores)} |"
                )

        with open("results/comparison_table.md", "w", encoding="utf-8") as f:
            f.write("\n".join(table_lines) + "\n")

        # Report 2: cost_analysis.md
        f_times = [r["flat_rag"]["time"] for r in data]
        g_times = [r["graph_rag"]["time"] for r in data]
        h_times = [r["hybrid_rag"]["time"] for r in data]
        f_ctx = [r["flat_rag"]["context_len"] for r in data]
        g_ctx = [r["graph_rag"]["context_len"] for r in data]
        h_ctx = [r["hybrid_rag"]["context_len"] for r in data]
        f_c = [r["flat_rag"]["metrics"]["correctness"] for r in data]
        g_c = [r["graph_rag"]["metrics"]["correctness"] for r in data]
        h_c = [r["hybrid_rag"]["metrics"]["correctness"] for r in data]

        cost_md = f"""# Cost and Performance Analysis

| Chỉ số (Indicator) | Flat RAG | Graph RAG | Hybrid RAG | Delta Best-F |
|---|---|---|---|---|
| **Accuracy (Avg)** | {np.mean(f_c):.2f} | {np.mean(g_c):.2f} | {np.mean(h_c):.2f} | - |
| **Response Time (Avg)** | {np.mean(f_times):.2f}s | {np.mean(g_times):.2f}s | {np.mean(h_times):.2f}s | - |
| **Latency (P95)** | {np.percentile(f_times, 95):.2f}s | {np.percentile(g_times, 95):.2f}s | {np.percentile(h_times, 95):.2f}s | - |
| **Context Size (Avg chars)** | {int(np.mean(f_ctx))} | {int(np.mean(g_ctx))} | {int(np.mean(h_ctx))} | - |
| **Faithfulness (Avg)** | {np.mean([r['flat_rag']['metrics']['faithfulness'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['faithfulness'] for r in data]):.2f} | {np.mean([r['hybrid_rag']['metrics']['faithfulness'] for r in data]):.2f} | - |
| **No-Hallucination (Avg)** | {np.mean([r['flat_rag']['metrics']['no_hallucination'] for r in data]):.2f} | {np.mean([r['graph_rag']['metrics']['no_hallucination'] for r in data]):.2f} | {np.mean([r['hybrid_rag']['metrics']['no_hallucination'] for r in data]):.2f} | - |
"""
        with open("results/cost_analysis.md", "w", encoding="utf-8") as f: f.write(cost_md)
        print("✅ Reports updated.")

if __name__ == "__main__":
    Evaluator().run_benchmark("benchmark/questions.json")
