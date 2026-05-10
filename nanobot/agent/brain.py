"""Unified Brain interface for Agent Zero."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nanobot.agent.context import ContextBuilder
from nanobot.agent.reasoning import ReasoningEngine
from nanobot.agent.working_memory import WorkingMemory
from nanobot.agent.memory import PersistentMemory
from nanobot.agent.planner import PhDPlanner
from nanobot.providers.base import LLMProvider, ToolCallRequest

class Brain:
    """
    The unified cognitive interface for Agent Zero.
    
    Ported from Agent Zero's core concept, enhanced with:
    - PhD Planning (PhDPlanner)
    - Persistent memory (PersistentMemory)
    - Deliberate monologue (ReasoningEngine)
    """
    
    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: Optional[str] = None,
        max_iterations: int = 15
    ):
        self.workspace = workspace
        self.working_memory = WorkingMemory()
        self.memory = PersistentMemory(workspace)
        self.planner = PhDPlanner()
        self.reasoning = ReasoningEngine(provider, model, max_iterations)
        self.context_builder = ContextBuilder(workspace)
        
    async def process_goal(
        self,
        goal: str,
        history: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        project_metadata: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[List[ToolCallRequest]], bool]:
        """
        Process a goal using the cognitive architecture.
        """
        # 1. Detect PhD Stage
        stage = self.planner.detect_phd_stage(project_metadata)
        
        # 2. Get Stage-specific context from memory
        memory_context = self.memory.get_context(stage)
        
        # 3. Build system prompt with Memory and Stage context
        system_prompt = self.context_builder.build_system_prompt()
        system_prompt += f"\n\n## PhD Research Stage: {stage.upper()}"
        system_prompt += f"\n{self.planner.get_stage_description(stage)}"
        system_prompt += f"\n\n## Relevant Research Memory\n{memory_context}"
        
        # 4. Use Reasoning Engine to deliberate
        content, tool_calls, is_complete = await self.reasoning.think(
            goal=goal,
            system_prompt=system_prompt,
            history=history,
            working_memory=self.working_memory,
            tools=tools
        )
        
        return content, tool_calls, is_complete

    async def store_result(self, task: Dict, result: Any, goal: str = ""):
        """Store a task result in persistent memory."""
        # Detect currently active stage
        stage = self.planner.detect_phd_stage() # Uses defaults or internal state
        await self.memory.store({
            "task": task,
            "result": result
        }, phd_stage=stage, goal=goal)

    def get_thought_trace(self) -> str:
        return self.reasoning.get_trace_summary()

    def reset(self):
        self.working_memory.clear()
        self.reasoning.thought_trace.clear()
        # Note: Persistent memory is NOT cleared on reset
