from typing import Any, List, Optional, Dict
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from modules.llm.adapters import BaseLLMAdapter
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FactoryAdapter(LLMProvider):
    """
    Adapts a BioDockify BaseLLMAdapter (from LLMFactory) to the NanoBot LLMProvider interface.
    Allows NanoBot's ReasoningEngine to use the system's global LLM configuration.
    """
    
    def __init__(self, adapter: BaseLLMAdapter):
        self.adapter = adapter
        # Try to guess model name from adapter attributes
        self.model_name = getattr(adapter, "model", "generic-model")
        super().__init__()

    def get_default_model(self) -> str:
        return self.model_name

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Convert NanoBot chat request to BaseLLMAdapter generate request.
        """
        try:
            # 1. Format Prompt
            full_prompt = self._messages_to_prompt(messages)
            
            if tools:
                try:
                    # Robust dumping
                    tools_desc = json.dumps(tools, indent=2, default=str)
                    full_prompt += f"\n\n[AVAILABLE TOOLS]\nYou have access to the following tools. To use one, output a JSON block like {{'tool': 'name', 'params': {{...}}}}:\n{tools_desc}\n"
                except Exception as e:
                    logger.error(f"Failed to serialize tools: {e}")
                    # Fallback so we don't crash
                    full_prompt += "\n\n[AVAILABLE TOOLS] (Serialization Failed)\n"

            # 2. Call Adapter
            logger.debug(f"FactoryAdapter calling adapter with prompt length {len(full_prompt)}")
            
            # Use run_in_executor explicitly if async_generate is suspected
            response_text = await self.adapter.async_generate(
                full_prompt, 
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 3. Parse Response
            tool_calls = self._extract_tool_calls(response_text, tools)
            
            return LLMResponse(
                content=response_text,
                tool_calls=tool_calls
            )
            
        except RecursionError:
            logger.error("RecursionError in FactoryAdapter.chat!")
            raise
        except Exception as e:
            logger.error(f"FactoryAdapter error: {e}")
            raise

    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Flatten messages to a single string prompt."""
        prompt_parts = []
        for msg in messages:
            role = str(msg.get("role", "user")).upper()
            content = str(msg.get("content", ""))
            prompt_parts.append(f"\n### {role}:\n{content}\n")
        
        prompt_parts.append("\n### ASSISTANT:\n")
        return "".join(prompt_parts)

    def _extract_tool_calls(self, content: str, tools: Optional[List[Dict]]) -> List[ToolCallRequest]:
        """Attempt to extract JSON tool calls from text."""
        calls = []
        if not tools: return calls
        
        try:
            # Regex for JSON blocks
            json_candidates = re.findall(r'(\{.*?\})', content, re.DOTALL)
            
            for json_str in json_candidates:
                try:
                    data = json.loads(json_str)
                    
                    name = data.get("tool") or data.get("name") or data.get("function")
                    params = data.get("params") or data.get("arguments") or data.get("args") or {}
                    
                    if name:
                         calls.append(ToolCallRequest(
                            id=f"call_{datetime.now().timestamp()}",
                            name=str(name),
                            arguments=params
                        ))
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"Tool extraction failed: {e}")
            
        return calls
