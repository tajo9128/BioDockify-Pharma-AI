"""Thesis API Routes for BioDockify AI

REST API endpoints for thesis generation using ThesisEngine.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.thesis.engine import get_thesis_engine
from modules.thesis.structure import PharmaBranch, DegreeType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/thesis", tags=["Thesis"])


class GenerateChapterRequest(BaseModel):
    chapter_id: str = Field(..., description="Chapter ID (e.g., 'introduction', 'methods', 'results')")
    topic: str = Field(..., description="Research topic")
    branch: str = Field(default="general", description="Pharma branch: general, clinical, pharmacology, pharmaceutical, medicinal, pharmacy")
    degree: str = Field(default="phd", description="Degree type: phd, pharm_d, msc, bsc")
    agent_mode: bool = Field(default=False, description="Use agent for generation (requires API key)")


class ChapterInfo(BaseModel):
    chapter_id: str
    title: str
    section_count: int


@router.get("/health")
async def health_check():
    """Health check for thesis module."""
    return {"status": "healthy", "module": "thesis"}


@router.get("/chapters")
async def get_chapters():
    """Get list of available thesis chapters."""
    try:
        engine = get_thesis_engine()
        chapters = engine.get_all_chapters()
        return {"status": "success", "chapters": chapters}
    except Exception as e:
        logger.error(f"Failed to get chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_chapter(request: GenerateChapterRequest):
    """Generate a thesis chapter."""
    try:
        engine = get_thesis_engine()

        branch_map = {
            "clinical": PharmaBranch.CLINICAL,
            "pharmacology": PharmaBranch.PHARMACOLOGY,
            "pharmaceutical": PharmaBranch.PHARMACEUTICAL,
            "medicinal": PharmaBranch.MEDICINAL,
            "pharmacy": PharmaBranch.PHARMACY,
        }
        degree_map = {
            "phd": DegreeType.PHD,
            "pharm_d": DegreeType.PHARM_D,
            "msc": DegreeType.MSC,
            "bsc": DegreeType.BSC,
        }

        branch = branch_map.get(request.branch.lower(), PharmaBranch.GENERAL)
        degree = degree_map.get(request.degree.lower(), DegreeType.PHD)

        result = await engine.generate_chapter(
            chapter_id=request.chapter_id,
            topic=request.topic,
            branch=branch,
            degree=degree
        )
        return result
    except Exception as e:
        logger.error(f"Chapter generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branches")
async def get_branches():
    """Get available pharma branches."""
    return {
        "branches": [
            {"id": b.value, "name": b.value.capitalize()}
            for b in PharmaBranch
        ]
    }


@router.get("/degrees")
async def get_degrees():
    """Get available degree types."""
    return {
        "degrees": [
            {"id": d.value, "name": d.value.replace("_", " ").upper()}
            for d in DegreeType
        ]
    }