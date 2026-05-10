"""
Hybrid Memory System - Combines ChromaDB (Advanced) with NanoBot's file memory.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import logging
from enum import Enum

from modules.memory.advanced_memory import (
    AdvancedMemorySystem, MemoryType, MemoryImportance, get_memory_system
)

logger = logging.getLogger(__name__)

class MemoryArea(Enum):
    MAIN = "main"
    FRAGMENTS = "fragments"
    SOLUTIONS = "solutions"
    INSTRUMENTS = "instruments"

    def to_memory_type(self) -> MemoryType:
        """Map legacy area to new memory types"""
        mapping = {
            MemoryArea.MAIN: MemoryType.EPISODIC,
            MemoryArea.FRAGMENTS: MemoryType.SEMANTIC,
            MemoryArea.SOLUTIONS: MemoryType.PROCEDURAL,
            MemoryArea.INSTRUMENTS: MemoryType.WORKING
        }
        return mapping.get(self, MemoryType.EPISODIC)

class HybridMemory:
    """
    Unified memory system:
    1. ChromaDB (AdvancedMemorySystem) for semantic search
    2. File-based daily notes (NanoBot style)
    """
    
    def __init__(self, workspace_path: str, memory_subdir: str = "default"):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "memory" / memory_subdir
        self.daily_dir = self.workspace / "memory" / "daily"
        
        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Advanced Memory System (ChromaDB)
        persist_path = str(self.memory_dir / "chroma_v2")
        self.advanced_memory = get_memory_system(persist_dir=persist_path)
        
    async def add_memory(
        self, 
        content: str, 
        area: MemoryArea = MemoryArea.MAIN,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add memory to both ChromaDB and daily log."""
        # 1. Add to daily log (Persistent Text)
        self._append_daily(content, area)
        
        # 2. Add to Advanced Memory (Vector Search)
        await self.advanced_memory.add_memory(
            content=content,
            memory_type=area.to_memory_type(),
            importance=importance,
            source="agent_zero_hybrid",
            metadata=metadata
        )
        
    def _append_daily(self, content: str, area: MemoryArea):
        """Append to today's markdown file."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.daily_dir / f"{today}.md"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n### [{timestamp}] {area.value.upper()}\n{content}\n"
        
        mode = "a" if daily_file.exists() else "w"
        with open(daily_file, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"# Daily Memory - {today}\n")
            f.write(entry)
            
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search memory using ChromaDB."""
        return await self.advanced_memory.search(query, limit=limit)
        
    def get_recent(self, days: int = 3) -> str:
        """Get recent daily logs."""
        from datetime import timedelta
        
        content = []
        today = datetime.now()
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            path = self.daily_dir / f"{date_str}.md"
            if path.exists():
                content.append(path.read_text(encoding="utf-8"))
                
        return "\n\n".join(content)
