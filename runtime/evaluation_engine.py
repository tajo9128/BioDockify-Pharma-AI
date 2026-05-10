import time
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger("BioDockify.Evaluation")

class EvaluationEngine:
    """
    Centralized engine for running benchmarks on RAG and Agent components.
    """
    
    def __init__(self, output_dir: str = "benchmarks/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

    async def run_all(self):
        """Run all registered benchmarks."""
        logger.info("Starting Full Benchmarking Suite...")
        
        # 1. RAG Benchmarks
        rag_results = await self.benchmark_rag()
        self.results.append({"type": "RAG", "data": rag_results})
        
        # 2. Agent Benchmarks
        agent_results = await self.benchmark_agent()
        self.results.append({"type": "Agent", "data": agent_results})
        
        # 3. Generate Report
        self.generate_report()

    async def benchmark_rag(self) -> Dict[str, Any]:
        """Runs benchmarks for the RAG system."""
        logger.info("Running RAG Benchmarks...")
        try:
            from tests.benchmarks.rag_eval import evaluate_rag_performance
            test_q = ["What is the primary target of Metformin?", "How does Hylan G-F 20 affect rat knees?"]
            test_gt = ["AMPK", "Delayed cartilage degeneration"]
            return await evaluate_rag_performance(test_q, test_gt)
        except Exception as e:
            logger.error(f"RAG Benchmark failed: {e}")
            return {"error": str(e)}

    async def benchmark_agent(self) -> Dict[str, Any]:
        """Runs benchmarks for Agent Zero tasks."""
        logger.info("Running Agent Benchmarks...")
        try:
            from tests.benchmarks.agent_eval import benchmark_agent_goals
            tasks = [
                "Find the molecular structure of Metformin.",
                "Summarize recent findings on COVID-19 mRNA vaccines."
            ]
            return await benchmark_agent_goals(tasks)
        except Exception as e:
            logger.error(f"Agent Benchmark failed: {e}")
            return {"error": str(e)}

    def generate_report(self):
        """Generates a Markdown report from the results."""
        report_path = self.output_dir / f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        content = [
            f"# BioDockify Benchmark Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## Summary\n"
        ]
        
        for result in self.results:
            content.append(f"### {result['type']} Performance")
            for k, v in result['data'].items():
                content.append(f"- **{k.replace('_', ' ').capitalize()}**: {v}")
            content.append("\n")
            
        with open(report_path, "w") as f:
            f.write("\n".join(content))
        
        logger.info(f"Report generated at: {report_path}")
        # Also symlink to latest
        latest_path = self.output_dir / "latest_report.md"
        if latest_path.exists():
            latest_path.unlink()
        try:
            # On Windows, symlinks might need admin, so we just copy
            import shutil
            shutil.copy(report_path, latest_path)
        except Exception:
            pass

if __name__ == "__main__":
    engine = EvaluationEngine()
    engine.run_all()
