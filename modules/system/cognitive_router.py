"""
BioDockify Cognitive Router (System Module)
Determines the active 'Persona' and activates the corresponding Pillar Subset.
"""

from enum import Enum
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class Persona(str, Enum):
    GENERAL_RESEARCH = "General Research"
    PHARMA_FACULTY = "Pharma Faculty"
    PHD_CANDIDATE = "PhD Candidate"
    INDUSTRIAL_SCIENTIST = "Industrial Scientist"
    INNOVATION_ENGINE = "Innovation Engine"
    BIOSTATISTICIAN = "Biostatistician"

class CognitiveRouter:
    """
    Routes user intent to the correct 40-Pillar Subset.
    """
    
    # Pillar definitions
    PILLARS = {
        Persona.GENERAL_RESEARCH: list(range(1, 7)),
        Persona.PHARMA_FACULTY: list(range(7, 11)),
        Persona.PHD_CANDIDATE: list(range(11, 16)),
        Persona.INDUSTRIAL_SCIENTIST: list(range(16, 22)),
        Persona.INNOVATION_ENGINE: list(range(22, 30)),
        Persona.BIOSTATISTICIAN: list(range(30, 41)) # 40 Pillars
    }
    
    # Keyword heuristics for simple routing (LLM-based routing is preferred but expensive)
    KEYWORDS = {
        Persona.BIOSTATISTICIAN: ["power", "sample size", "survival", "km", "cox", "forest plot", "sap", "heor", "icer", "budget impact"],
        Persona.INNOVATION_ENGINE: ["novelty", "target", "hypothesis", "chemical space", "smiles", "scaffold", "blue sky"],
        Persona.INDUSTRIAL_SCIENTIST: ["ind", "clinical", "gxp", "cmc", "manufacturing", "regulatory", "audit", "compliance", "pipeline"],
        Persona.PHD_CANDIDATE: ["thesis", "dissertation", "defense", "viva", "novelty score", "gap analysis"],
        Persona.PHARMA_FACULTY: ["grant", "funding", "tenure", "supervision", "lab management", "curriculum"]
    }

    def route_intent(self, user_query: str) -> Tuple[Persona, List[int]]:
        """
        Determines the active persona and pillar subset.
        """
        query_lower = user_query.lower()
        
        # Check specific personas first (ordered by specificity)
        for persona, keywords in self.KEYWORDS.items():
            if any(k in query_lower for k in keywords):
                logger.info(f"Cognitive Router: Switching to {persona.value}")
                return persona, self.PILLARS[persona]
                
        # Default fallback
        logger.info("Cognitive Router: Defaulting to General Research")
        return Persona.GENERAL_RESEARCH, self.PILLARS[Persona.GENERAL_RESEARCH]

    def get_system_prompt_addition(self, persona: Persona) -> str:
        """
        Generates the system prompt injection for the active persona.
        """
        base = f"\n\n### ACTIVE MODE: {persona.value.upper()}\n"
        
        if persona == Persona.PHARMA_FACULTY:
            base += "You are a Tenured Professor. Focus on Funding, Strategy, and Supervision.\n"
        elif persona == Persona.PHD_CANDIDATE:
            base += "You are a PhD Candidate. Focus on Novelty, Thesis Structure, and Defense Preparation.\n"
        elif persona == Persona.INDUSTRIAL_SCIENTIST:
            base += "You are an R&D Scientist. Focus on Regulatory Compliance (FDA/EMA), GxP, and Pipeline Milestones.\n"
        elif persona == Persona.INNOVATION_ENGINE:
            base += "You are a Discovery Scientist. Focus on Target ID, Chemical Space, and Blue Sky Hypothesis Generation.\n"
        elif persona == Persona.BIOSTATISTICIAN:
            base += "You are a Senior Biostatistician. Focus on Study Design, Power Calculation, SAP Generation, and HEOR.\n"
            
        return base
