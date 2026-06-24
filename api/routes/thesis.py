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
    branch: str = Field(default="general", description="Pharma branch: general, clinical, pharmacology, pharmaceutics, pharmacognosy, pharma_chemistry, regulatory, pharma_analysis")
    degree: str = Field(default="phd", description="Degree type: phd, m_pharm, b_pharm, pharm_d")
    agent_mode: bool = Field(default=False, description="Use agent for generation (requires API key)")


class ChapterInfo(BaseModel):
    chapter_id: str
    title: str
    section_count: int


# ── Branch/Degree Map (matches UI values → real enums) ──
BRANCH_MAP = {
    "general": PharmaBranch.GENERAL,
    "clinical": PharmaBranch.CLINICAL_PHARMACY,
    "pharmacology": PharmaBranch.PHARMACOLOGY,
    "pharmaceutics": PharmaBranch.PHARMACEUTICS,
    "pharmacognosy": PharmaBranch.PHARMACOGNOSY,
    "pharma_chemistry": PharmaBranch.PHARMA_CHEMISTRY,
    "regulatory": PharmaBranch.REGULATORY,
    "pharma_analysis": PharmaBranch.PHARMA_ANALYSIS,
}
DEGREE_MAP = {
    "phd": DegreeType.PHD,
    "m_pharm": DegreeType.M_PHARM,
    "b_pharm": DegreeType.B_PHARM,
    "pharm_d": DegreeType.PHARM_D,
}


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
    """Generate a thesis chapter (primary endpoint)."""
    return await _do_generate(request)


@router.post("/generate-chapter")
async def generate_chapter_alias(request: GenerateChapterRequest):
    """Generate a thesis chapter (alias — matches UI call)."""
    return await _do_generate(request)


async def _do_generate(request: GenerateChapterRequest):
    """Shared generation logic."""
    try:
        engine = get_thesis_engine()
        branch = BRANCH_MAP.get(request.branch.lower(), PharmaBranch.GENERAL)
        degree = DEGREE_MAP.get(request.degree.lower(), DegreeType.PHD)

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
            {"id": k, "name": v.value}
            for k, v in BRANCH_MAP.items()
        ]
    }


@router.get("/degrees")
async def get_degrees():
    """Get available degree types."""
    return {
        "degrees": [
            {"id": k, "name": v.value}
            for k, v in DEGREE_MAP.items()
        ]
    }