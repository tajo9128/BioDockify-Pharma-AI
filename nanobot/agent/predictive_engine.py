"""
Predictive Resource Modeling - BioDockify NanoBot
Handles time forecasting, disk growth estimation, and compute projection.
"""
import logging
import psutil
from typing import Dict, Any, List
from nanobot.agent.working_memory import WorkingMemory

logger = logging.getLogger("nanobot.predictive_engine")

class PredictiveResourceEngine:
    """
    Forecats resource usage for research plans.
    """
    
    def __init__(self, reasoning_engine):
        self.brain = reasoning_engine

    async def forecast_resources(self, methodology: str, working_memory: WorkingMemory) -> Dict[str, Any]:
        """
        Estimate resource requirements for a given methodology.
        """
        # Get current system stats for baseline
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        disk_free_gb = psutil.disk_usage('/').free / (1024**3)
        
        goal = f"Forecast resource usage for this methodology:\n\n{methodology}"
        
        system_prompt = f"""
You are the Resource Forecaster for BioDockify. 
Current System Context: {cpu_count} CPUs, {memory_gb:.1f}GB RAM, {disk_free_gb:.1f}GB Disk Free.

Estimate the following for the provided research methodology:
1. **Estimated Execution Time**: Total time to complete all phases.
2. **Disk Usage Growth**: Projected data size (outputs, logs, datasets).
3. **Compute Load**: CPU/GPU utilization intensity.
4. **Completion Probability**: Confidence score (%) that the system can finish this project given current resources.

Output the results as a clean JSON object.
"""
        
        response, _, _ = await self.brain.think(
            goal=goal,
            system_prompt=system_prompt,
            history=[],
            working_memory=working_memory,
            tools=[]
        )
        
        return {
            "forecast": response,
            "system_snapshot": {
                "cpu": cpu_count,
                "ram_gb": round(memory_gb, 1),
                "disk_free_gb": round(disk_free_gb, 1)
            }
        }
