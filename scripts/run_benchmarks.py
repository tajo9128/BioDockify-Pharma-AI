import sys
import argparse
import logging
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from runtime.evaluation_engine import EvaluationEngine

def main():
    parser = argparse.ArgumentParser(description="BioDockify Benchmarking Tool")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--rag", action="store_true", help="Run only RAG benchmarks")
    parser.add_argument("--agent", action="store_true", help="Run only Agent benchmarks")
    parser.add_argument("--output", type=str, default="benchmarks/results", help="Output directory")
    
    args = parser.parse_args()
    
    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    engine = EvaluationEngine(output_dir=args.output)
    
    if args.all or (not args.rag and not args.agent):
        asyncio.run(engine.run_all())
    elif args.rag:
        rag_res = asyncio.run(engine.benchmark_rag())
        engine.results.append({"type": "RAG", "data": rag_res})
        engine.generate_report()
    elif args.agent:
        agent_res = asyncio.run(engine.benchmark_agent())
        engine.results.append({"type": "Agent", "data": agent_res})
        engine.generate_report()

if __name__ == "__main__":
    main()
