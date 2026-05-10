"""
User Memory Tool - Store and recall facts about the user.
"""
import logging

class UserMemoryTool:
    """Manage long-term user facts."""
    
    def __init__(self, memory):
        self.memory = memory
        
    async def save_fact(self, fact: str):
        """Save a permanent fact about the user."""
        await self.memory.add_memory(f"USER FACT: {fact}", area="main")
        return f"Saved fact: {fact}"
        
    async def recall_facts(self, query: str) -> str:
        """Recall relevant facts."""
        # Simple search
        return "Memory integration pending"
