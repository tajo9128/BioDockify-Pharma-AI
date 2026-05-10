#!/usr/bin/env python3
"""
BioDockify Research CLI
Command-line interface for running the BioDockify Pharma Research AI.
"""

import argparse
import sys
import logging
from orchestration.planner.orchestrator import ResearchOrchestrator, OrchestratorConfig
from orchestration.executor import ResearchExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description="BioDockify Pharma Research AI")
    parser.add_argument("--title", type=str, required=True, help="Research topic title")
    parser.add_argument("--mode", choices=["local", "cloud"], default="local", help="AI Inference Mode")
    parser.add_argument("--output", type=str, help="Output file for results (optional)")
    
    args = parser.parse_args()
    
    print(f"\n[+] BioDockify Research AI")
    print(f"========================================")
    print(f"Topic: {args.title}")
    print(f"Mode:  {args.mode}")
    print(f"========================================\n")

    # 1. Initialize Orchestrator
    config = OrchestratorConfig(
        use_cloud_api=(args.mode == "cloud"),
        ollama_host="http://localhost:11434" # Default
    )
    orchestrator = ResearchOrchestrator(config)

    # 2. Plan Research
    print(">>> Phase 1: Planning Research...")
    try:
        plan = orchestrator.plan_research(args.title)
    except Exception as e:
        print(f"CRITICAL ERROR: Planning failed: {e}")
        sys.exit(1)
        
    print(f"[+] Plan generated with {len(plan.steps)} steps.\n")

    # 3. Execute Research
    print(">>> Phase 2: Executing Research...")
    executor = ResearchExecutor()
    context = executor.execute_plan(plan)
    
    # 4. Report Results
    print("\n========================================")
    print("RESEARCH COMPLETE")
    print("========================================")
    print(f"Extracted Text: {len(context.extracted_text)} chars")
    print(f"Entities Found: { sum(len(v) for v in context.entities.values()) }")
    if context.analyst_stats:
        print(f"Knowledge Graph Stats: {context.analyst_stats}")
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(f"Research Report: {args.title}\n")
            f.write(context.extracted_text[:1000]) # Sample
        print(f"\nResuls saved to {args.output}")

if __name__ == "__main__":
    main()
