"""
Agent Zero - Sub-Agent System
Allows Agent Zero to spawn subordinate agents for subtask delegation.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("sub_agent")


class AgentStatus(Enum):
    """Status of a sub-agent."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgent:
    """
    Represents a subordinate agent that handles a specific subtask.
    Inherits constitution from parent but has focused context.
    """
    id: str
    parent_id: Optional[str]
    task: str
    role: str
    depth: int
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "task": self.task,
            "role": self.role,
            "depth": self.depth,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "children": self.children
        }


class SubAgentManager:
    """
    Manages the hierarchy of sub-agents.
    Enforces max depth and tracks all agents in the tree.
    """
    
    MAX_DEPTH = 3  # Maximum sub-agent nesting depth
    MAX_CHILDREN = 5  # Maximum children per agent
    
    def __init__(self):
        self.agents: Dict[str, SubAgent] = {}
        self.root_agent_id: Optional[str] = None
    
    def create_root_agent(self, task: str) -> SubAgent:
        """Create the root agent (Agent Zero himself)."""
        agent = SubAgent(
            id=f"agent-0-{uuid.uuid4().hex[:8]}",
            parent_id=None,
            task=task,
            role="Primary Research Orchestrator",
            depth=0
        )
        self.agents[agent.id] = agent
        self.root_agent_id = agent.id
        logger.info(f"Created root agent: {agent.id}")
        return agent
    
    def spawn_subagent(
        self,
        parent_id: str,
        task: str,
        role: str
    ) -> Optional[SubAgent]:
        """
        Spawn a new sub-agent under the given parent.
        
        Args:
            parent_id: ID of the parent agent
            task: Specific task for the sub-agent
            role: Role/specialization of the sub-agent
        
        Returns:
            The new SubAgent, or None if constraints violated
        """
        parent = self.agents.get(parent_id)
        if not parent:
            logger.error(f"Parent agent not found: {parent_id}")
            return None
        
        # Check depth constraint
        if parent.depth >= self.MAX_DEPTH:
            logger.warning(f"Max depth ({self.MAX_DEPTH}) reached for agent {parent_id}")
            return None
        
        # Check children limit
        if len(parent.children) >= self.MAX_CHILDREN:
            logger.warning(f"Max children ({self.MAX_CHILDREN}) reached for agent {parent_id}")
            return None
        
        # Create the sub-agent
        agent = SubAgent(
            id=f"agent-{parent.depth + 1}-{uuid.uuid4().hex[:8]}",
            parent_id=parent_id,
            task=task,
            role=role,
            depth=parent.depth + 1,
            context={"inherited_from": parent.role}
        )
        
        self.agents[agent.id] = agent
        parent.children.append(agent.id)
        
        logger.info(f"Spawned sub-agent {agent.id} (depth={agent.depth}) under {parent_id}")
        return agent
    
    def update_status(
        self,
        agent_id: str,
        status: AgentStatus,
        result: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update an agent's status and result."""
        agent = self.agents.get(agent_id)
        if not agent:
            return
        
        agent.status = status
        if status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED]:
            agent.completed_at = datetime.now()
        if result:
            agent.result = result
        if error:
            agent.error = error
        
        logger.info(f"Agent {agent_id} status updated to {status.value}")
    
    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def get_children(self, agent_id: str) -> List[SubAgent]:
        """Get all direct children of an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []
        return [self.agents[cid] for cid in agent.children if cid in self.agents]
    
    def get_hierarchy(self) -> Dict[str, Any]:
        """Get the full agent hierarchy as a tree."""
        if not self.root_agent_id:
            return {}
        
        def build_tree(agent_id: str) -> Dict[str, Any]:
            agent = self.agents.get(agent_id)
            if not agent:
                return {}
            
            tree = agent.to_dict()
            tree["children_details"] = [
                build_tree(cid) for cid in agent.children
            ]
            return tree
        
        return build_tree(self.root_agent_id)
    
    def get_pending_agents(self) -> List[SubAgent]:
        """Get all agents that are still pending."""
        return [a for a in self.agents.values() if a.status == AgentStatus.PENDING]
    
    def aggregate_results(self, agent_id: str) -> str:
        """Aggregate results from an agent and all its descendants."""
        agent = self.agents.get(agent_id)
        if not agent:
            return ""
        
        results = []
        if agent.result:
            results.append(f"[{agent.role}]: {agent.result}")
        
        for child_id in agent.children:
            child_results = self.aggregate_results(child_id)
            if child_results:
                results.append(child_results)
        
        return "\n".join(results)
    
    def cancel_all(self):
        """Cancel all pending/running agents."""
        for agent in self.agents.values():
            if agent.status in [AgentStatus.PENDING, AgentStatus.RUNNING]:
                self.update_status(agent.id, AgentStatus.CANCELLED)
    
    def reset(self):
        """Clear all agents and start fresh."""
        self.agents.clear()
        self.root_agent_id = None


# Global manager instance
sub_agent_manager = SubAgentManager()


# Helper functions for API integration
def spawn_subagent(parent_id: str, task: str, role: str) -> Dict[str, Any]:
    """API-friendly function to spawn a sub-agent."""
    agent = sub_agent_manager.spawn_subagent(parent_id, task, role)
    if agent:
        return {
            "status": "success",
            "agent_id": agent.id,
            "depth": agent.depth,
            "message": f"Sub-agent '{role}' spawned successfully."
        }
    else:
        return {
            "status": "error",
            "message": "Failed to spawn sub-agent. Max depth or children limit reached."
        }


def get_agent_status(agent_id: str) -> Dict[str, Any]:
    """API-friendly function to get agent status."""
    agent = sub_agent_manager.get_agent(agent_id)
    if agent:
        return {"status": "success", "agent": agent.to_dict()}
    else:
        return {"status": "error", "message": "Agent not found."}
