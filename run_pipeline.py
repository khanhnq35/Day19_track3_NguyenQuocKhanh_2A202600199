"""End-to-end pipeline runner for FlatRAG vs GraphRAG.

This script runs corpus preparation, FlatRAG indexing, GraphRAG triple extraction,
Neo4j graph building, benchmark evaluation, and report generation. It also
measures build-time cost proxies required by the lab: elapsed time and estimated
token usage for each build stage.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from src.data_fetcher import COMPANIES, fetch_wikipedia_data
from src.entity_extraction import EntityExtractor
from src.evaluation import Evaluator
from src.flat_rag import FlatRAG
from src.graph_builder import GraphBuilder


@dataclass
class BuildCost:
    """Build-stage cost metrics.

    Attributes:
        stage: Pipeline stage name.
        elapsed_seconds: Wall-clock time in seconds.
        input_tokens_est: Estimated input token count.
        output_tokens_est: Estimated output token count.
        total_tokens_est: Estimated total token count.
        notes: Extra details about stage behavior.
    """

    stage: str
    elapsed_seconds: float
    input_tokens_est: int
    output_tokens_est: int
    total_tokens_est: int
    notes: str


class PipelineRunner:
    """Run complete GraphRAG and FlatRAG pipeline with build-cost reporting."""

    def __init__(
        self,
        corpus_path: str = "data/tech_company_corpus.txt",
        triples_path: str = "data/triples.json",
        benchmark_path: str = "benchmark/questions.json",
        results_dir: str = "results",
    ) -> None:
        """Initialize paths for full pipeline.

        Args:
            corpus_path: Corpus text path.
            triples_path: Extracted triples JSON path.
            benchmark_path: Benchmark questions JSON path.
            results_dir: Report output directory.
        """
        self.corpus_path = Path(corpus_path)
        self.triples_path = Path(triples_path)
        self.benchmark_path = Path(benchmark_path)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.costs: list[BuildCost] = []

    def run(
        self,
        skip_fetch: bool = False,
        skip_graph_build: bool = False,
        skip_evaluation: bool = False,
    ) -> None:
        """Run complete pipeline.

        Args:
            skip_fetch: Reuse existing corpus when true.
            skip_graph_build: Skip Neo4j insertion when true.
            skip_evaluation: Skip benchmark evaluation when true.
        """
        print("🚀 Start full RAG pipeline")
        self._ensure_parent_dirs()

        if not skip_fetch or not self.corpus_path.exists():
            self._measure_stage(
                stage="corpus_fetch",
                func=lambda: fetch_wikipedia_data(COMPANIES, str(self.corpus_path)),
                input_text="\n".join(COMPANIES),
                output_path=self.corpus_path,
                notes="Wikipedia corpus collection; no LLM token cost.",
            )
        else:
            print("⏭️ Skip corpus fetch; existing corpus used.")

        self._measure_stage(
            stage="flat_rag_build",
            func=lambda: FlatRAG().ingest_corpus(str(self.corpus_path)),
            input_text=self._read_text(self.corpus_path),
            output_path=None,
            notes="FlatRAG Chroma embedding/index build. Token estimate = corpus tokens embedded.",
        )

        self._measure_stage(
            stage="graph_rag_triple_extraction",
            func=lambda: EntityExtractor().process_corpus(
                str(self.corpus_path),
                str(self.triples_path),
            ),
            input_text=self._read_text(self.corpus_path),
            output_path=self.triples_path,
            notes="GraphRAG LLM triple extraction. Token estimate covers corpus input and triples output.",
        )

        if not skip_graph_build:
            self._measure_stage(
                stage="graph_rag_neo4j_build",
                func=self._build_neo4j_graph,
                input_text=self._read_text(self.triples_path),
                output_path=None,
                notes="Neo4j graph construction from triples; no LLM token cost beyond triples input proxy.",
            )
        else:
            print("⏭️ Skip Neo4j graph build.")

        self._write_build_cost_report()

        if not skip_evaluation:
            if not self.benchmark_path.exists():
                raise FileNotFoundError(
                    f"Benchmark file not found: {self.benchmark_path}. "
                    "Create benchmark/questions.json first."
                )
            Evaluator().run_benchmark(str(self.benchmark_path))
            self._append_build_cost_to_cost_analysis()
        else:
            print("⏭️ Skip evaluation.")

        print("✅ Pipeline completed.")

    def _ensure_parent_dirs(self) -> None:
        """Create required output directories."""
        self.corpus_path.parent.mkdir(parents=True, exist_ok=True)
        self.triples_path.parent.mkdir(parents=True, exist_ok=True)
        self.benchmark_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_neo4j_graph(self) -> None:
        """Create constraints and build Neo4j graph."""
        builder = GraphBuilder()
        try:
            builder.create_constraints()
            builder.build_graph(str(self.triples_path))
            builder.verify_graph()
        finally:
            builder.close()

    def _measure_stage(
        self,
        stage: str,
        func: Callable[[], Any],
        input_text: str,
        output_path: Path | None,
        notes: str,
    ) -> None:
        """Measure one pipeline stage.

        Args:
            stage: Stage name.
            func: Callable stage body.
            input_text: Text used for input token estimate.
            output_path: Optional file path for output token estimate.
            notes: Cost notes.
        """
        print(f"▶️ Running stage: {stage}")
        start_time = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start_time

        output_text = self._read_text(output_path) if output_path else ""
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        self.costs.append(
            BuildCost(
                stage=stage,
                elapsed_seconds=elapsed,
                input_tokens_est=input_tokens,
                output_tokens_est=output_tokens,
                total_tokens_est=total_tokens,
                notes=notes,
            )
        )
        print(
            f"✅ {stage}: {elapsed:.2f}s, "
            f"~{total_tokens:,} tokens (input={input_tokens:,}, output={output_tokens:,})"
        )

    def _write_build_cost_report(self) -> None:
        """Write standalone build cost reports in JSON and Markdown."""
        json_path = self.results_dir / "build_costs.json"
        md_path = self.results_dir / "build_costs.md"

        json_path.write_text(
            json.dumps([asdict(cost) for cost in self.costs], indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        rows = [
            "# Build Cost Report",
            "",
            "| Stage | Time (s) | Input Tokens (est.) | Output Tokens (est.) | Total Tokens (est.) | Notes |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for cost in self.costs:
            rows.append(
                "| "
                f"{cost.stage} | "
                f"{cost.elapsed_seconds:.2f} | "
                f"{cost.input_tokens_est:,} | "
                f"{cost.output_tokens_est:,} | "
                f"{cost.total_tokens_est:,} | "
                f"{cost.notes} |"
            )

        graph_costs = [cost for cost in self.costs if cost.stage.startswith("graph_rag")]
        flat_costs = [cost for cost in self.costs if cost.stage.startswith("flat_rag")]
        rows.extend(
            [
                "",
                "## Build Summary",
                "",
                "| Pipeline | Build Time (s) | Build Tokens (est.) |",
                "|---|---:|---:|",
                f"| FlatRAG | {sum(cost.elapsed_seconds for cost in flat_costs):.2f} | {sum(cost.total_tokens_est for cost in flat_costs):,} |",
                f"| GraphRAG | {sum(cost.elapsed_seconds for cost in graph_costs):.2f} | {sum(cost.total_tokens_est for cost in graph_costs):,} |",
                "",
                "> Token usage is estimated with `ceil(chars / 4)` because current LangChain calls do not expose provider usage metadata consistently.",
            ]
        )
        md_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"📄 Build cost report written: {md_path}")

    def _append_build_cost_to_cost_analysis(self) -> None:
        """Append build-cost section to existing cost analysis report."""
        cost_analysis_path = self.results_dir / "cost_analysis.md"
        build_report_path = self.results_dir / "build_costs.md"
        if not cost_analysis_path.exists() or not build_report_path.exists():
            return

        current = cost_analysis_path.read_text(encoding="utf-8")
        build_report = build_report_path.read_text(encoding="utf-8")
        marker = "\n\n---\n\n# Build Cost Report\n"
        trimmed = current.split("\n\n---\n\n# Build Cost Report\n", maxsplit=1)[0]
        cost_analysis_path.write_text(
            f"{trimmed}{marker}{build_report.split('# Build Cost Report', maxsplit=1)[1].lstrip()}",
            encoding="utf-8",
        )
        print(f"📄 Build cost appended: {cost_analysis_path}")

    def _read_text(self, path: Path | None) -> str:
        """Read text safely.

        Args:
            path: Optional text path.

        Returns:
            File content or empty string.
        """
        if path is None or not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using common 4 chars/token heuristic.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser(description="Run full FlatRAG and GraphRAG pipeline.")
    parser.add_argument("--skip-fetch", action="store_true", help="Reuse existing corpus file.")
    parser.add_argument("--skip-graph-build", action="store_true", help="Skip Neo4j graph insertion.")
    parser.add_argument("--skip-evaluation", action="store_true", help="Skip benchmark evaluation.")
    parser.add_argument("--corpus-path", default="data/tech_company_corpus.txt")
    parser.add_argument("--triples-path", default="data/triples.json")
    parser.add_argument("--benchmark-path", default="benchmark/questions.json")
    parser.add_argument("--results-dir", default="results")
    return parser.parse_args()


def main() -> None:
    """Run CLI entrypoint."""
    args = parse_args()
    runner = PipelineRunner(
        corpus_path=args.corpus_path,
        triples_path=args.triples_path,
        benchmark_path=args.benchmark_path,
        results_dir=args.results_dir,
    )
    runner.run(
        skip_fetch=args.skip_fetch,
        skip_graph_build=args.skip_graph_build,
        skip_evaluation=args.skip_evaluation,
    )


if __name__ == "__main__":
    main()
