"""
Deep Research Orchestrator
Main pipeline connecting Discovery, Screening, Headless Retrieval, and Synthesis.
"""
import logging
import asyncio
from typing import Dict, Any, List

from .discovery import discovery_engine
from .screening import ContentScreener
from .synthesis import synthesis_engine

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
        
        # Phase 3: Full-Text Retrieval + DOCX Storage
        status.append(f"Phase 3: Full-Text Retrieval - Downloading {len(selected_papers)} papers...")
        from modules.literature.full_text import FullTextRetriever
        from modules.export.literature_docx import LiteratureDocxExporter
        from api.knowledge import _store_docx_entry

        retriever = FullTextRetriever()
        exporter = LiteratureDocxExporter()
        full_text_papers = []
        docx_stored = 0

        for i, paper in enumerate(selected_papers):
            paper_dict = {
                "title": paper.title,
                "url": paper.url,
                "source": paper.source,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "year": str(paper.year) if paper.year else "",
                "doi": paper.doi,
                "pdf_url": paper.pdf_url,
            }

            logger.info(f"Retrieving ({i+1}/{len(selected_papers)}): {paper.title[:80]}...")
            full_text = retriever.retrieve(paper_dict)

            if full_text:
                try:
                    docx_bytes = exporter.export_article(paper_dict, full_text)
                    _store_docx_entry(
                        category="literature",
                        title=paper.title,
                        docx_bytes=docx_bytes,
                        tags="deep_research,full_text",
                        source=paper.source,
                        metadata={"doi": paper.doi, "year": paper.year}
                    )
                    docx_stored += 1
                    full_text_papers.append(paper)
                    status.append(f"  [{i+1}] FULL: {paper.title[:60]} ({len(full_text)} chars)")
                except Exception as e:
                    logger.warning(f"DOCX storage failed for {paper.title}: {e}")
                    status.append(f"  [{i+1}] PARTIAL: {paper.title[:60]} (retrieved but storage failed)")
            else:
                try:
                    docx_bytes = exporter.export_article(paper_dict, None)
                    _store_docx_entry(
                        category="literature",
                        title=paper.title,
                        docx_bytes=docx_bytes,
                        tags="deep_research,abstract_only",
                        source=paper.source,
                        metadata={"doi": paper.doi, "year": paper.year}
                    )
                    docx_stored += 1
                    status.append(f"  [{i+1}] ABSTRACT: {paper.title[:60]} (full text unavailable)")
                except Exception as e:
                    logger.warning(f"Abstract DOCX failed for {paper.title}: {e}")
                    status.append(f"  [{i+1}] FAIL: {paper.title[:60]}")

        logger.info(f"Full-text retrieved: {len(full_text_papers)}/{len(selected_papers)}, DOCX stored: {docx_stored}")
        status.append(f"Full-text: {len(full_text_papers)}/{len(selected_papers)} | DOCX: {docx_stored} saved to Knowledge Base")
        
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
            "papers_full_text": len(full_text_papers),
            "docx_stored": docx_stored,
            "report_content": report,
            "compliance_report": compliance_result,
            "pipeline_log": status
        }

# Singleton
orchestrator = DeepResearchOrchestrator()
