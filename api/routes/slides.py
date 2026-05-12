"""Slides API Routes for BioDockify AI

REST API endpoints for presentation generation using SlideGenerator.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.slides.slide_generator import get_slide_generator
from modules.slides.slide_styles import get_available_styles

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/slides", tags=["Slides"])


class GenerateFromKBRequest(BaseModel):
    topic: str = Field(..., description="Research topic for the presentation")
    style: str = Field(default="academic", description="Presentation style")
    num_slides: int = Field(default=10, ge=3, le=30, description="Number of slides")
    include_citations: bool = Field(default=True, description="Include source citations")


class GenerateFromPromptRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of desired slides")
    style: str = Field(default="academic", description="Presentation style")
    num_slides: int = Field(default=10, ge=3, le=30, description="Number of slides")


class AssembleSlidesRequest(BaseModel):
    topic: str = Field(..., description="Presentation topic")
    slide_contents: List[Dict[str, str]] = Field(..., description="List of {title, content, notes, type}")
    style: str = Field(default="academic", description="Presentation style")


@router.get("/styles")
async def get_styles():
    """Get available presentation styles."""
    try:
        styles = get_available_styles()
        return {"status": "success", "styles": styles}
    except Exception as e:
        logger.error(f"Failed to get styles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for slides module."""
    return {"status": "healthy", "module": "slides"}


@router.post("/generate/from-kb")
async def generate_from_knowledge_base(request: GenerateFromKBRequest):
    """Generate slides from the knowledge base."""
    try:
        generator = get_slide_generator()
        result = generator.generate_from_knowledge_base(
            topic=request.topic,
            style=request.style,
            num_slides=request.num_slides,
            include_citations=request.include_citations
        )
        return result
    except Exception as e:
        logger.error(f"Slide generation from KB failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/from-prompt")
async def generate_from_prompt(request: GenerateFromPromptRequest):
    """Generate slides from a natural language prompt."""
    try:
        generator = get_slide_generator()
        result = generator.generate_from_prompt(
            prompt=request.prompt,
            style=request.style,
            num_slides=request.num_slides
        )
        return result
    except Exception as e:
        logger.error(f"Slide generation from prompt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assemble")
async def assemble_slides(request: AssembleSlidesRequest):
    """Assemble slides from pre-generated content."""
    try:
        generator = get_slide_generator()
        result = generator.assemble_slides(
            topic=request.topic,
            slide_contents=request.slide_contents,
            style=request.style
        )
        return result
    except Exception as e:
        logger.error(f"Slide assembly failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare-for-agent")
async def prepare_for_agent(topic: str, style: str = "academic", num_slides: int = 10):
    """Prepare slide generation task for agent to process."""
    try:
        generator = get_slide_generator()
        result = generator.prepare_for_agent(
            topic=topic,
            style=style,
            num_slides=num_slides
        )
        return result
    except Exception as e:
        logger.error(f"Prepare for agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))