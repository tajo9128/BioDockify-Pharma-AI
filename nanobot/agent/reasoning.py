"""Reasoning engine for the Agent Zero monologue loop."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from nanobot.providers.base import LLMProvider, ToolCallRequest

class RepairableException(Exception):
    """Exception that the agent can potentially fix by retrying with different parameters."""
    pass

class ReasoningEngine:
    """
    The core reasoning engine that implements the "monologue loop".
    Enhanced with self-healing and robust multi-format tool parsing.
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        model: Optional[str] = None,
        max_iterations: int = 15
    ):
        self.provider = provider
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.thought_trace: List[Dict[str, Any]] = []
        
    async def think(
        self,
        goal: str,
        system_prompt: str,
        history: List[Dict[str, Any]],
        working_memory: Any,
        tools: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[List[ToolCallRequest]], bool]:
        """Conduct a single reasoning step or deliberate on the goal."""
        
        # Build the reasoning prompt
        enhanced_system_prompt = f"{system_prompt}\n\n## Current Goal\n{goal}\n\n## Internal Deliberation\n{working_memory.format_for_prompt()}"
        
        messages = [{"role": "system", "content": enhanced_system_prompt}]
        messages.extend(history)
        
        logger.debug(f"[Reasoning] Thinking about goal: {goal}")
        
        try:
            response = await self.provider.chat(
                messages=messages,
                tools=tools,
                model=self.model
            )
            
            # Robust parsing for non-native tool calls (JSON/Markdown)
            tool_calls = response.tool_calls or []
            if not tool_calls and response.content:
                tool_calls = self._parse_manual_tool_calls(response.content, tools)

            # Record the thought
            self.thought_trace.append({
                "timestamp": datetime.now().isoformat(),
                "content": response.content,
                "tool_calls": [tc.__dict__ for tc in tool_calls] if tool_calls else []
            })
            
            if response.content:
                working_memory.add_thought(response.content)
                
            is_final = not bool(tool_calls) and bool(response.content)
            return response.content, tool_calls, is_final

        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            raise RepairableException(f"Reasoning failure: {str(e)}")

    def _parse_manual_tool_calls(self, content: str, available_tools: List[Dict]) -> List[ToolCallRequest]:
        """Extract tool calls from text if model didn't use native tool calling."""
        calls = []
        
        # 1. Try JSON block parsing
        json_match = re.search(r'```json\s*(\{.*\}|\[.*\])\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict): data = [data]
                for item in data:
                    name = item.get("tool") or item.get("name")
                    args = item.get("params") or item.get("arguments") or {}
                    if name:
                        calls.append(ToolCallRequest(id=f"manual_{datetime.now().timestamp()}", name=name, arguments=args))
            except: pass

        # 2. Try legacy string format (tool: name params)
        if not calls:
            for marker in ["tool:", "call:", "execute:"]:
                if marker in content.lower():
                    # Simplified extraction
                    parts = content.lower().split(marker, 1)[1].strip().split(None, 1)
                    name = parts[0].strip(": \n")
                    args = {"input": parts[1].strip()} if len(parts) > 1 else {}
                    calls.append(ToolCallRequest(id=f"manual_{datetime.now().timestamp()}", name=name, arguments=args))
                    break
        
        return calls

    def get_trace_summary(self) -> str:
        summary = []
        for i, step in enumerate(self.thought_trace):
            summary.append(f"### Step {i+1}\n{step['content']}")
            if step['tool_calls']:
                tools = ", ".join([tc['name'] for tc in step['tool_calls']])
                summary.append(f"*Action: {tools}*")
        return "\n\n".join(summary)
