"""
Strategic Planner Capabilities - BioDockify NanoBot
Handles research structuring, methodology design, and title architecture.
"""
import logging
from typing import Dict, Any, List, Optional
import json

from nanobot.agent.working_memory import WorkingMemory
from nanobot.agent.risk_engine import RiskIntelligenceEngine
from nanobot.agent.predictive_engine import PredictiveResourceEngine
from nanobot.utils.reproducibility import ReproducibilityEngine
from pathlib import Path

logger = logging.getLogger("nanobot.planner")

class ResearchPlannerCapabilities:
    """
    Core logic for NanoBot's Strategic Research Planner role.
    Translates user sparks into structured methodologies.
    """
    
    def __init__(self, reasoning_engine, project_root: str = "./data/workspace"):
        self.brain = reasoning_engine
        self.risk_engine = RiskIntelligenceEngine(reasoning_engine)
        self.predictive_engine = PredictiveResourceEngine(reasoning_engine)
        self.repro_engine = ReproducibilityEngine(Path(project_root))

    async def craft_title(self, prompt: str, working_memory: WorkingMemory) -> str:
        """Generate high-impact academic titles."""
        goal = f"Generate 3 academically rigorous and high-impact research titles based on the user spark: '{prompt}'."
        system_prompt = "You are the Title Architect for a pharmaceutical research AI. Your goal is to create compelling, professional, and precise academic titles."
        
        response, _, _ = await self.brain.think(
            goal=goal,
            system_prompt=system_prompt,
            history=[],
            working_memory=working_memory,
            tools=[]
        )
        return response

    async def design_methodology(self, spark: str, working_memory: WorkingMemory) -> Dict[str, Any]:
        """Convert a vague idea into a structured methodology."""
        goal = f"Design a step-by-step research methodology for the following idea: '{spark}'. " \
               "Analyze feasibility and provide a structured plan with at least 5 phases."
        
        system_prompt = """
You are the Strategic Research Planner for BioDockify. 
Your goal is to convert vague research ideas into actionable, phased methodologies.
Provide the output in a structured format:
- Title
- Background
- Objectives
- Methodology (Phased)
- Feasibility Assessment
"""
        
        response, _, _ = await self.brain.think(
            goal=goal,
            system_prompt=system_prompt,
            history=[],
            working_memory=working_memory,
            tools=[]
        )
        return {"methodology": response}

    async def generate_roadmap(self, methodology: str, working_memory: WorkingMemory) -> List[Dict[str, Any]]:
        """Turn a methodology into a list of technical tasks for Agent Zero."""
        goal = f"Convert this methodology into a JSON list of technical tasks for Agent Zero: \n\n{methodology}"
        system_prompt = "You are the Project Structurer. Your goal is to create a technical roadmap. Output ONLY a JSON list of task objects with 'title' and 'category' (e.g., literature_search, entity_extraction, data_analysis)."
        
        response, _, _ = await self.brain.think(
            goal=goal,
            system_prompt=system_prompt,
            history=[],
            working_memory=working_memory,
            tools=[]
        )
        
        try:
            # Attempt to parse JSON if the LLM followed instructions
            tasks = json.loads(response)
            return tasks
        except:
             logger.warning("LLM failed to provide structured JSON for roadmap. Returning raw text as 'task'.")
             return [{"title": "Execute Methodology", "description": response, "category": "custom"}]

    async def evaluate_strategy(self, methodology: str, working_memory: WorkingMemory) -> Dict[str, Any]:
        """Perform a dual risk and resource evaluation of a methodology."""
        risks = await self.risk_engine.analyze_project_risks(methodology, working_memory)
        forecast = await self.predictive_engine.forecast_resources(methodology, working_memory)
        
        return {
            "risks": risks,
            "forecast": forecast
        }

    async def freeze_project_state(self, 
                                   label: str, 
                                   project_metadata: Optional[Dict[str, Any]] = None,
                                   dataset_path: Optional[str] = None,
                                   parameters: Optional[Dict[str, Any]] = None,
                                   workflow_state: Optional[Dict[str, Any]] = None,
                                   outputs: Optional[Dict[str, Any]] = None) -> str:
        """Capture a multi-layered reproducibility snapshot."""
        # Merge legacy metadata into parameters if provided
        final_params = parameters or {}
        if project_metadata:
            final_params.update(project_metadata)
            
        return await self.repro_engine.create_snapshot(
            label=label,
            dataset_path=dataset_path,
            parameters=final_params,
            workflow_state=workflow_state,
            outputs=outputs
        )

