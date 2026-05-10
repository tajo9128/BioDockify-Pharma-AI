"""Working memory for transient reasoning state."""

from datetime import datetime
from typing import Any, Dict, List, Optional


class WorkingMemory:
    """
    Scratchpad and transient state manager for the current reasoning session.
    
    Stores thoughts, derived facts, and arbitrary key-value state that the
    agent uses during its monologue loop.
    """
    
    def __init__(self):
        self.scratchpad: Dict[str, Any] = {}
        self.thought_queue: List[Dict[str, Any]] = []
        self.facts: List[Dict[str, Any]] = []
        self.last_updated: datetime = datetime.now()
    
    def add_thought(self, thought: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a thought to the reasoning queue."""
        self.thought_queue.append({
            "thought": thought,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self._touch()
    
    def add_fact(self, fact: str, confidence: float = 1.0) -> None:
        """Add a derived fact with a confidence score."""
        self.facts.append({
            "fact": fact,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        self._touch()
    
    def set_scratchpad(self, key: str, value: Any) -> None:
        """Set a value in the transient scratchpad."""
        self.scratchpad[key] = value
        self._touch()
    
    def get_scratchpad(self, key: str, default: Any = None) -> Any:
        """Get a value from the scratchpad."""
        return self.scratchpad.get(key, default)
    
    def clear(self) -> None:
        """Clear all working memory."""
        self.scratchpad.clear()
        self.thought_queue.clear()
        self.facts.clear()
        self._touch()
    
    def _touch(self) -> None:
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get a summary of working memory for the prompt context.
        Returns the last 10 thoughts and all current facts/scratchpad.
        """
        return {
            "recent_thoughts": [t["thought"] for t in self.thought_queue[-10:]],
            "known_facts": [f["fact"] for f in self.facts],
            "scratchpad": self.scratchpad
        }
    
    def format_for_prompt(self) -> str:
        """Format working memory as a markdown string for inclusion in prompts."""
        parts = []
        
        if self.facts:
            facts_str = "\n".join([f"- {f['fact']}" for f in self.facts])
            parts.append(f"### Current Facts\n{facts_str}")
        
        if self.thought_queue:
            thoughts_str = "\n".join([f"- {t['thought']}" for t in self.thought_queue[-5:]])
            parts.append(f"### Recent Thoughts\n{thoughts_str}")
            
        if self.scratchpad:
            scratch_str = "\n".join([f"- **{k}**: {v}" for k, v in self.scratchpad.items()])
            parts.append(f"### Scratchpad\n{scratch_str}")
            
        return "\n\n".join(parts) if parts else "Working memory is currently empty."
