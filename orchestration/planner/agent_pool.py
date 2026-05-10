"""
Agent Pool - Parallel Task Execution via Sub-Agents

This module provides the ability to spawn sub-agents for parallel
execution of independent research tasks, significantly speeding up
operations like multi-database literature searches.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution."""
    agent_id: str
    task_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    attempts: int = 1


@dataclass
class SubAgent:
    """
    A lightweight sub-agent for executing a single task.
    
    Sub-agents are spawned by the AgentPool and execute tasks
    in parallel with other sub-agents.
    """
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_id: Optional[str] = None
    task: Optional[Dict] = None
    status: str = "idle"  # idle, running, completed, failed
    result: Optional[SubAgentResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    async def execute(self, task: Dict, executor_func) -> SubAgentResult:
        """
        Execute the assigned task.
        
        Args:
            task: Task dictionary with task details
            executor_func: Async function to execute the task
            
        Returns:
            SubAgentResult with execution outcome
        """
        self.task = task
        self.status = "running"
        start_time = datetime.now()
        
        logger.info(f"[SubAgent {self.agent_id}] Starting task: {task.get('title', 'unknown')}")
        
        try:
            result = await executor_func(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.result = SubAgentResult(
                agent_id=self.agent_id,
                task_name=task.get("title", "unknown"),
                success=True,
                data=result,
                execution_time_seconds=execution_time
            )
            self.status = "completed"
            
            logger.info(f"[SubAgent {self.agent_id}] Completed in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.result = SubAgentResult(
                agent_id=self.agent_id,
                task_name=task.get("title", "unknown"),
                success=False,
                error=str(e),
                execution_time_seconds=execution_time
            )
            self.status = "failed"
            
            logger.error(f"[SubAgent {self.agent_id}] Failed: {e}")
            
        return self.result


class AgentPool:
    """
    Pool of sub-agents for parallel task execution.
    
    Features:
    - Spawn sub-agents on demand
    - Execute tasks in parallel with concurrency limits
    - Aggregate results from all sub-agents
    - Track execution history
    """
    
    def __init__(
        self, 
        max_concurrent: int = 3,
        parent_id: Optional[str] = None
    ):
        """
        Initialize the agent pool.
        
        Args:
            max_concurrent: Maximum number of concurrent sub-agents
            parent_id: ID of the parent agent/orchestrator
        """
        self.max_concurrent = max_concurrent
        self.parent_id = parent_id or str(uuid.uuid4())[:8]
        self.agents: List[SubAgent] = []
        self.execution_history: List[Dict] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    def spawn_agent(self) -> SubAgent:
        """
        Create a new sub-agent.
        
        Returns:
            New SubAgent instance
        """
        agent = SubAgent(parent_id=self.parent_id)
        self.agents.append(agent)
        logger.info(f"[AgentPool] Spawned agent {agent.agent_id}")
        return agent
        
    async def execute_parallel(
        self, 
        tasks: List[Dict],
        executor_func
    ) -> List[SubAgentResult]:
        """
        Execute multiple tasks in parallel using sub-agents.
        
        Args:
            tasks: List of task dictionaries
            executor_func: Async function to execute each task
            
        Returns:
            List of SubAgentResult from all tasks
        """
        if not tasks:
            return []
            
        start_time = datetime.now()
        logger.info(f"[AgentPool] Starting parallel execution of {len(tasks)} tasks")
        
        async def execute_with_semaphore(task: Dict) -> SubAgentResult:
            async with self._semaphore:
                agent = self.spawn_agent()
                return await agent.execute(task, executor_func)
                
        # Execute all tasks concurrently (limited by semaphore)
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(SubAgentResult(
                    agent_id="error",
                    task_name=tasks[i].get("title", "unknown"),
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
                
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Log execution summary
        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful
        
        execution_record = {
            "timestamp": start_time.isoformat(),
            "total_tasks": len(tasks),
            "successful": successful,
            "failed": failed,
            "total_time_seconds": total_time,
            "tasks": [r.task_name for r in processed_results]
        }
        self.execution_history.append(execution_record)
        
        logger.info(
            f"[AgentPool] Completed {len(tasks)} tasks in {total_time:.2f}s "
            f"(Success: {successful}, Failed: {failed})"
        )
        
        return processed_results
        
    def aggregate_results(
        self, 
        results: List[SubAgentResult],
        merge_strategy: str = "concatenate"
    ) -> Dict:
        """
        Aggregate results from multiple sub-agents.
        
        Args:
            results: List of SubAgentResult
            merge_strategy: How to merge results ("concatenate" or "merge_dicts")
            
        Returns:
            Aggregated result dictionary
        """
        aggregated = {
            "success": all(r.success for r in results),
            "total_results": len(results),
            "successful_count": sum(1 for r in results if r.success),
            "failed_count": sum(1 for r in results if not r.success),
            "data": [],
            "errors": []
        }
        
        for result in results:
            if result.success and result.data:
                if merge_strategy == "concatenate":
                    if isinstance(result.data, list):
                        aggregated["data"].extend(result.data)
                    else:
                        aggregated["data"].append(result.data)
                elif merge_strategy == "merge_dicts" and isinstance(result.data, dict):
                    for key, value in result.data.items():
                        if key not in aggregated["data"]:
                            aggregated["data"][key] = []
                        aggregated["data"][key].append(value)
            elif result.error:
                aggregated["errors"].append({
                    "task": result.task_name,
                    "error": result.error
                })
                
        return aggregated
        
    def can_parallelize(self, tasks: List[Dict]) -> bool:
        """
        Determine if tasks can be safely parallelized.
        
        Tasks can be parallel if they have no dependencies on each other.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            True if tasks can run in parallel
        """
        # Check for explicit dependencies
        for task in tasks:
            deps = task.get("dependencies", [])
            if deps:
                # Check if any dependency is in the current task list
                task_ids = {t.get("step_id") or t.get("id") for t in tasks}
                if any(d in task_ids for d in deps):
                    return False
                    
        # Check for conflicting categories (e.g., write operations to same resource)
        categories = [t.get("category", "") for t in tasks]
        write_categories = {"write", "update", "delete", "modify"}
        write_tasks = [c for c in categories if any(w in c.lower() for w in write_categories)]
        
        # If multiple write tasks, don't parallelize
        if len(write_tasks) > 1:
            return False
            
        return True
        
    def get_pool_status(self) -> Dict:
        """
        Get current status of the agent pool.
        
        Returns:
            Status dictionary
        """
        return {
            "parent_id": self.parent_id,
            "max_concurrent": self.max_concurrent,
            "total_agents_spawned": len(self.agents),
            "agents_by_status": {
                "idle": sum(1 for a in self.agents if a.status == "idle"),
                "running": sum(1 for a in self.agents if a.status == "running"),
                "completed": sum(1 for a in self.agents if a.status == "completed"),
                "failed": sum(1 for a in self.agents if a.status == "failed")
            },
            "total_executions": len(self.execution_history)
        }
        
    def cleanup(self):
        """Clean up completed agents to free memory."""
        completed = [a for a in self.agents if a.status in ("completed", "failed")]
        for agent in completed:
            self.agents.remove(agent)
        logger.info(f"[AgentPool] Cleaned up {len(completed)} completed agents")
