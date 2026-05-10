"""
SlideGenerator - Generate presentations from Knowledge Base content
Agent Zero handles AI content generation - this module manages structure and export.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("slide_generator")


class SlideGenerator:
    """
    Generates professional presentation slides from various Knowledge Base sources.
    
    Supports:
    - Full Knowledge Base queries by topic
    - Search results conversion
    - Custom prompt-based generation
    - Selected document compilation
    - Agent Zero integration for AI-powered content generation
    """
    
    def __init__(self, llm_adapter=None, rag_engine=None):
        """
        Initialize the SlideGenerator.
        
        Args:
            llm_adapter: LLM adapter for content generation (legacy)
            rag_engine: RAG engine for Knowledge Base queries
        """
        self.llm = llm_adapter
        self.rag = rag_engine
        self.generation_history = []
        self._agent_callback: Optional[Callable] = None
    
    def set_agent_callback(self, callback: Callable[[str], str]):
        """
        Set the Agent Zero callback for content generation.
        
        Args:
            callback: Function that takes a prompt and returns generated content
        """
        self._agent_callback = callback
    
    def prepare_for_agent(
        self,
        topic: str,
        style: str = "academic",
        num_slides: int = 10
    ) -> Dict[str, Any]:
        """
        Prepare slide generation data for Agent Zero to process.
        
        Returns structured data for Agent Zero's content generation.
        """
        # Query RAG for context
        relevant_content = self._query_rag(topic, top_k=num_slides * 2)
        
        return {
            "task": "slide_generation",
            "topic": topic,
            "style": style,
            "num_slides": num_slides,
            "suggested_structure": [
                {"slide": 1, "type": "title", "title": topic},
                {"slide": 2, "type": "overview", "title": "Outline"},
                *[{"slide": i + 3, "type": "content", "title": f"Key Point {i + 1}"} 
                  for i in range(num_slides - 3)],
                {"slide": num_slides, "type": "conclusion", "title": "Conclusions"}
            ],
            "context": [
                {"text": c.get("text", "")[:500], "source": c.get("metadata", {}).get("source", "")}
                for c in relevant_content[:10]
            ]
        }
    
    def assemble_slides(
        self,
        topic: str,
        slide_contents: List[Dict[str, str]],
        style: str = "academic"
    ) -> Dict[str, Any]:
        """
        Assemble slides from Agent Zero generated content.
        
        Args:
            topic: Presentation topic
            slide_contents: List of dicts with title, content, notes
            style: Presentation style
        
        Returns:
            Complete slide presentation data
        """
        from .slide_styles import get_style_template
        
        template = get_style_template(style)
        slides = []
        
        for i, item in enumerate(slide_contents):
            slide = {
                "index": i + 1,
                "type": item.get("type", "content"),
                "title": item.get("title", f"Slide {i + 1}"),
                "content": item.get("content", ""),
                "notes": item.get("notes", ""),
                "style": template
            }
            slides.append(slide)
        
        result = {
            "status": "success",
            "topic": topic,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "generated_at": datetime.now().isoformat()
        }
        
        self.generation_history.append(result)
        return result
    
    def generate_from_knowledge_base(
        self,
        topic: str,
        style: str = "academic",
        num_slides: int = 10,
        include_citations: bool = True
    ) -> Dict[str, Any]:
        """
        Query the entire Knowledge Base and generate topic-focused slides.
        
        Args:
            topic: Research topic to focus on
            style: Presentation style (academic, modern, minimal)
            num_slides: Target number of slides
            include_citations: Whether to include source citations
        
        Returns:
            Dict with slides content and metadata
        """
        logger.info(f"Generating slides from KB: topic='{topic}', style={style}, slides={num_slides}")
        
        # Step 1: Query RAG for relevant content
        relevant_content = self._query_rag(topic, top_k=num_slides * 3)
        
        # Step 2: Generate slide outline
        outline = self._generate_outline(topic, relevant_content, num_slides)
        
        # Step 3: Generate individual slides
        slides = self._generate_slides(outline, style, include_citations)
        
        result = {
            "status": "success",
            "topic": topic,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "citations": self._extract_citations(relevant_content) if include_citations else [],
            "generated_at": datetime.now().isoformat()
        }
        
        self.generation_history.append(result)
        return result
    
    def generate_from_search(
        self,
        search_results: List[Dict[str, Any]],
        style: str = "academic",
        title: str = "Research Findings"
    ) -> Dict[str, Any]:
        """
        Generate slides from search results with citations.
        
        Args:
            search_results: List of search result objects with text and metadata
            style: Presentation style
            title: Presentation title
        
        Returns:
            Dict with slides content and metadata
        """
        logger.info(f"Generating slides from {len(search_results)} search results")
        
        # Convert search results to content
        content_items = [
            {
                "text": r.get("text", r.get("content", "")),
                "source": r.get("metadata", {}).get("source", "Unknown"),
                "score": r.get("score", 0)
            }
            for r in search_results
        ]
        
        # Generate slides from content
        slides = self._generate_slides_from_content(content_items, style, title)
        
        return {
            "status": "success",
            "title": title,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "source_count": len(search_results),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_from_prompt(
        self,
        prompt: str,
        style: str = "academic",
        num_slides: int = 10
    ) -> Dict[str, Any]:
        """
        Generate slides based on a custom user description.
        
        Args:
            prompt: User's natural language description of desired slides
            style: Presentation style
            num_slides: Target number of slides
        
        Returns:
            Dict with slides content and metadata
        """
        logger.info(f"Generating slides from prompt: '{prompt[:50]}...'")
        
        # Use LLM to interpret prompt and generate content
        if not self.llm:
            return self._generate_fallback_slides(prompt, style, num_slides)
        
        # Generate slide content using LLM
        system_prompt = self._get_slide_generation_prompt(style, num_slides)
        response = self.llm.generate(f"{system_prompt}\n\nUser Request: {prompt}")
        
        # Parse LLM response into slides
        slides = self._parse_llm_slides(response)
        
        return {
            "status": "success",
            "prompt": prompt,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_from_documents(
        self,
        document_ids: List[str],
        style: str = "academic",
        title: str = "Document Summary"
    ) -> Dict[str, Any]:
        """
        Generate slides from specific selected documents.
        
        Args:
            document_ids: List of document IDs from the library
            style: Presentation style
            title: Presentation title
        
        Returns:
            Dict with slides content and metadata
        """
        logger.info(f"Generating slides from {len(document_ids)} documents")
        
        # Retrieve document content
        documents = self._retrieve_documents(document_ids)
        
        # Generate slides from document content
        slides = self._generate_slides_from_documents(documents, style, title)
        
        return {
            "status": "success",
            "title": title,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "document_count": len(documents),
            "generated_at": datetime.now().isoformat()
        }
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    def _query_rag(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Query the RAG engine for relevant content."""
        if self.rag:
            try:
                results = self.rag.search(query, top_k=top_k)
                return results
            except Exception as e:
                logger.error(f"RAG query failed: {e}")
        return []
    
    def _generate_outline(
        self,
        topic: str,
        content: List[Dict[str, Any]],
        num_slides: int
    ) -> List[Dict[str, str]]:
        """Generate a slide outline from content."""
        # Default outline structure
        outline = [
            {"type": "title", "title": topic, "subtitle": "Research Overview"},
            {"type": "overview", "title": "Outline", "content": "Key topics covered"},
        ]
        
        # Add content slides
        for i, item in enumerate(content[:num_slides - 3]):
            outline.append({
                "type": "content",
                "title": f"Key Finding {i + 1}",
                "content": item.get("text", "")[:500]
            })
        
        # Add conclusion
        outline.append({
            "type": "conclusion",
            "title": "Conclusions",
            "content": "Summary of key findings"
        })
        
        return outline[:num_slides]
    
    def _generate_slides(
        self,
        outline: List[Dict[str, str]],
        style: str,
        include_citations: bool
    ) -> List[Dict[str, Any]]:
        """Generate individual slides from outline."""
        from .slide_styles import get_style_template
        
        template = get_style_template(style)
        slides = []
        
        for i, item in enumerate(outline):
            slide = {
                "index": i + 1,
                "type": item.get("type", "content"),
                "title": item.get("title", f"Slide {i + 1}"),
                "content": item.get("content", ""),
                "style": template,
                "notes": ""
            }
            slides.append(slide)
        
        return slides
    
    def _generate_slides_from_content(
        self,
        content_items: List[Dict[str, Any]],
        style: str,
        title: str
    ) -> List[Dict[str, Any]]:
        """Generate slides from content items."""
        slides = [
            {
                "index": 1,
                "type": "title",
                "title": title,
                "content": f"Generated from {len(content_items)} sources",
                "style": style
            }
        ]
        
        for i, item in enumerate(content_items[:15]):  # Max 15 content slides
            slides.append({
                "index": i + 2,
                "type": "content",
                "title": f"Finding {i + 1}",
                "content": item.get("text", "")[:400],
                "source": item.get("source", ""),
                "style": style
            })
        
        # Add references slide
        slides.append({
            "index": len(slides) + 1,
            "type": "references",
            "title": "References",
            "content": "\n".join([f"• {item.get('source', 'Unknown')}" for item in content_items[:10]]),
            "style": style
        })
        
        return slides
    
    def _generate_slides_from_documents(
        self,
        documents: List[Dict[str, Any]],
        style: str,
        title: str
    ) -> List[Dict[str, Any]]:
        """Generate slides from document content."""
        # Similar to content-based generation
        content_items = [
            {"text": doc.get("content", ""), "source": doc.get("filename", "Unknown")}
            for doc in documents
        ]
        return self._generate_slides_from_content(content_items, style, title)
    
    def _generate_fallback_slides(
        self,
        prompt: str,
        style: str,
        num_slides: int
    ) -> Dict[str, Any]:
        """Generate basic slides when LLM is not available."""
        slides = [
            {
                "index": 1,
                "type": "title",
                "title": "Presentation",
                "content": prompt[:100],
                "style": style
            }
        ]
        
        for i in range(2, min(num_slides, 5) + 1):
            slides.append({
                "index": i,
                "type": "content",
                "title": f"Section {i - 1}",
                "content": f"Content for section {i - 1}",
                "style": style
            })
        
        return {
            "status": "success",
            "prompt": prompt,
            "style": style,
            "num_slides": len(slides),
            "slides": slides,
            "note": "Generated without LLM - add API key for better results",
            "generated_at": datetime.now().isoformat()
        }
    
    def _retrieve_documents(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve document content from library."""
        # This would integrate with the library/store module
        documents = []
        for doc_id in document_ids:
            # Placeholder - would actually query the library
            documents.append({
                "id": doc_id,
                "filename": f"document_{doc_id}",
                "content": ""
            })
        return documents
    
    def _extract_citations(self, content: List[Dict[str, Any]]) -> List[str]:
        """Extract citations from content items."""
        citations = []
        for item in content:
            source = item.get("metadata", {}).get("source", "")
            if source and source not in citations:
                citations.append(source)
        return citations
    
    def _get_slide_generation_prompt(self, style: str, num_slides: int) -> str:
        """Get the system prompt for slide generation."""
        return f"""You are a professional presentation designer. Create exactly {num_slides} slides 
in {style} style. For each slide, provide:
- SLIDE [number]: [title]
- CONTENT: [main content, 2-3 bullet points]
- NOTES: [speaker notes]

Keep content concise and impactful. Use academic language for scholarly topics."""
    
    def _parse_llm_slides(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured slides."""
        slides = []
        lines = response.split("\n")
        current_slide = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("SLIDE"):
                if current_slide:
                    slides.append(current_slide)
                # Parse slide header
                try:
                    parts = line.split(":", 1)
                    title = parts[1].strip() if len(parts) > 1 else f"Slide {len(slides) + 1}"
                    current_slide = {
                        "index": len(slides) + 1,
                        "type": "content",
                        "title": title,
                        "content": "",
                        "notes": ""
                    }
                except:
                    current_slide = {"index": len(slides) + 1, "type": "content", "title": "", "content": "", "notes": ""}
            elif line.startswith("CONTENT:") and current_slide:
                current_slide["content"] = line[8:].strip()
            elif line.startswith("NOTES:") and current_slide:
                current_slide["notes"] = line[6:].strip()
            elif current_slide and line and not line.startswith(("SLIDE", "CONTENT:", "NOTES:")):
                # Append to content
                current_slide["content"] += "\n" + line
        
        if current_slide:
            slides.append(current_slide)
        
        return slides


# Singleton instance for convenience
_generator_instance = None


def get_slide_generator(llm_adapter=None, rag_engine=None) -> SlideGenerator:
    """Get or create the SlideGenerator singleton."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SlideGenerator(llm_adapter, rag_engine)
    return _generator_instance
