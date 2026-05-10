"""
Persistent Memory - Long-term research retention system.
Ported from Agent Zero original core.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from nanobot.utils.helpers import ensure_dir

logger = logging.getLogger(__name__)

class PersistentMemory:
    """
    Persistent memory system for Agent Zero.
    Supports short-term session memory and long-term disk retrieval.
    """

    def __init__(
        self, 
        workspace: Path, 
        max_long_term: int = 1000,
        max_short_term: int = 50
    ):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.long_term_file = self.memory_dir / "long_term.json"
        
        self.max_long_term = max_long_term
        self.max_short_term = max_short_term
        
        self.short_term: List[Dict] = []
        self.long_term: List[Dict] = []
        
        self._load_long_term()

    async def store(
        self, 
        entry: Dict, 
        phd_stage: str = "unknown",
        goal: str = ""
    ) -> str:
        """Store a memory entry."""
        timestamp = datetime.now().isoformat()
        
        memory_item = {
            "timestamp": timestamp,
            "phd_stage": phd_stage,
            "goal": goal,
            **entry
        }
        
        # Add to short-term
        self.short_term.append(memory_item)
        if len(self.short_term) > self.max_short_term:
            self.short_term.pop(0)
            
        # Add to long-term
        self.long_term.append(memory_item)
        if len(self.long_term) > self.max_long_term:
            self.long_term.pop(0)
            
        self._save_long_term()
        return timestamp

    def recall(self, query: str, limit: int = 5, phd_stage: Optional[str] = None) -> List[Dict]:
        """Recall relevant memories using simple keyword matching."""
        results = []
        query_words = set(query.lower().split())
        
        for item in reversed(self.long_term):
            if phd_stage and item.get("phd_stage") != phd_stage:
                continue
                
            match_score = 0
            item_str = json.dumps(item).lower()
            for word in query_words:
                if word in item_str:
                    match_score += 1
            
            if match_score > 0:
                results.append((item, match_score))
                
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]

    def get_context(self, phd_stage: str, max_memories: int = 10) -> str:
        """Get formatted context for prompts."""
        relevant = [
            m for m in self.long_term 
            if m.get("phd_stage") == phd_stage
        ][-max_memories:]
        
        if not relevant:
            return "No previous research context for this stage."
            
        context_parts = []
        for m in reversed(relevant):
            context_parts.append(
                f"[{m.get('timestamp')}] {m.get('phd_stage').upper()}: {m.get('goal')}\n"
                f"Result: {str(m.get('result', 'No result'))[:200]}..."
            )
            
        return "\n\n".join(context_parts)

    def _load_long_term(self):
        if self.long_term_file.exists():
            try:
                self.long_term = json.loads(self.long_term_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load long-term memory: {e}")
                self.long_term = []

    def _save_long_term(self):
        try:
            self.long_term_file.write_text(
                json.dumps(self.long_term, indent=2), 
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")

    # Compatibility methods for NanoBot bridge
    def append_today(self, content: str) -> None:
        """Legacy support for daily notes."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.long_term.append({
            "timestamp": timestamp,
            "type": "note",
            "content": content,
            "phd_stage": "general"
        })
        self._save_long_term()

    def get_memory_context(self) -> str:
        """Legacy support for context building."""
        return self.get_context("general", max_memories=5)
