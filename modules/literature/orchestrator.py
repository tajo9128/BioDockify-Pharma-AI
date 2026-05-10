"""
Deep Research Orchestrator
Main pipeline connecting Discovery, Screening, Headless Retrieval, and Synthesis.
"""
import logging
import asyncio
from typing import Dict, Any

from .discovery import discovery_engine
from .screening import ContentScreener
from .synthesis import synthesis_engine
from modules.headless_research import HeadlessResearcher

logger = logging.getLogger("literature.orchestrator")

class DeepResearchOrchestrator:
    def __init__(self):
        self.screener = ContentScreener()
        
    async def run_deep_review(self, topic: str) -> Dict[str, Any]:
        """
        Run the full autonomous literature review pipeline.
        1. Discover candidates (API)
        2. Screen for relevance (AI)
        3. Deep Retrieve full text (Headless)
        4. Synthesize report (RAG)
        """
        logger.info(f"Starting Deep Research for: {topic}")
        status = []
        
        # Phase 1: Discovery
        status.append("Phase 1: Discovery - Aggregating sources...")
        candidates = await discovery_engine.search(topic, limit=20)
        logger.info(f"Found {len(candidates)} candidate papers")
        
        # Phase 2: Screening
        status.append(f"Phase 2: Screening - Analyzing {len(candidates)} candidates...")
        selected_papers = await self.screener.screen_papers(candidates, criteria=f"Relevant to {topic}")
        logger.info(f"Selected {len(selected_papers)} papers for deep review")
        
        # Phase 3: Deep Retrieval
        if not selected_papers:
            return {"error": "No papers selected after screening", "status": status}
            
        status.append(f"Phase 3: Retrieval - Reading {len(selected_papers)} papers...")
        async with HeadlessResearcher() as researcher:
            for i, paper in enumerate(selected_papers):
                # Try to find a link
                # Priority: PDF URL -> DOI Link -> URL
                target_url = paper.pdf_url or (f"https://doi.org/{paper.doi}" if paper.doi else paper.url)
                
                if target_url:
                    logger.info(f"Crawling ({i+1}/{len(selected_papers)}): {paper.title}")
                    try:
                        await researcher.research(target_url)
                        # research() automatically syncs to KB/SurfSense
                    except Exception as e:
                        logger.error(f"Failed to crawl {paper.title}: {e}")
        
        # Phase 4: Synthesis
        status.append("Phase 4: Synthesis - Writing report...")
        report = await synthesis_engine.generate_review(topic, selected_papers)
        
        # Phase 5: Plagiarism & Compliance Gate
        status.append("Phase 5: Compliance - Running Plagiarism Check...")
        from modules.compliance import plagiarism_checker
        
        # Clean report markdown for checking (remove titles/formatting potentially)
        # For now, check the raw report
        compliance_result = await plagiarism_checker.check_content(report)
        status.append(f"Compliance Result: {compliance_result['status']} (Similarity: {compliance_result['overall_similarity']}%)")
        
        if compliance_result['status'] == "BLOCKED":
            logger.warning(f"Report BLOCKED due to high plagiarism risk: {compliance_result['overall_similarity']}%")
            return {
                "status": "blocked",
                "reason": "Plagiarism Check Failed",
                "compliance_report": compliance_result,
                "pipeline_log": status
            }
            
        elif compliance_result['status'] == "FLAGGED":
             status.append("WARNING: Moderate similarity detected. Review recommended.")
             # In future: Trigger rewrite loop here.
             
        return {
            "status": "success",
            "topic": topic,
            "papers_found": len(candidates),
            "papers_reviewed": len(selected_papers),
            "report_content": report,
            "compliance_report": compliance_result, # Include for audit
            "pipeline_log": status
        }

# Singleton
orchestrator = DeepResearchOrchestrator()
