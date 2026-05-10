
"""
Auto-Research Orchestrator
Manages full-length PhD, grand, and review article research workflows.
Plans, executes, stores, and communicates research automatically.
"""
import logging
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from .research_detector import ResearchTopicDetector, ResearchTopic

logger = logging.getLogger(__name__)

class ResearchStage(Enum):
    """Research workflow stages."""
    DETECTED = "detected"
    PLANNING = "planning"
    TODO_GENERATED = "todo_generated"
    DEEP_RESEARCH = "deep_research"
    WEB_SCRAPING = "web_scraping"
    ANALYSIS = "analysis"
    STORAGE = "storage"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ResearchTask:
    """Individual research task in todo list."""
    id: str
    title: str
    description: str
    status: str  # "pending", "in_progress", "completed", "failed"
    priority: int  # 1-5, 5 = highest
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ResearchPlan:
    """Complete research plan with stages and tasks."""
    topic: str
    research_type: str
    stages: Dict[str, List[str]]
    tasks: List[ResearchTask]
    current_stage: ResearchStage = ResearchStage.DETECTED
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

class TodoListManager:
    """
    Manages todo list for research tasks.
    Handles task creation, dependencies, and progress tracking.
    """
    
    def __init__(self):
        self.tasks: Dict[str, ResearchTask] = {}
        self.task_counter = 0
    
    def create_task(
        self,
        title: str,
        description: str,
        priority: int = 3,
        dependencies: List[str] = None
    ) -> ResearchTask:
        """Create a new research task."""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        task = ResearchTask(
            id=task_id,
            title=title,
            description=description,
            status="pending",
            priority=priority,
            dependencies=dependencies or []
        )
        
        self.tasks[task_id] = task
        logger.info(f"Created task: {task_id} - {title}")
        return task
    
    def update_task_status(self, task_id: str, status: str, result: str = None):
        """Update task status and optional result."""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if result:
                self.tasks[task_id].result = result
            logger.info(f"Updated task {task_id} to {status}")
    
    def get_pending_tasks(self, priority_threshold: int = 0) -> List[ResearchTask]:
        """Get tasks ready to execute (no pending dependencies)."""
        pending = []
        for task in self.tasks.values():
            if task.status != "pending":
                continue
            if task.priority < priority_threshold:
                continue
            
            # Check dependencies
            deps_met = all(
                self.tasks[dep_id].status == "completed"
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )
            
            if deps_met:
                pending.append(task)
        
        # Sort by priority (highest first)
        pending.sort(key=lambda t: -t.priority)
        return pending
    
    def get_progress(self) -> float:
        """Calculate overall progress (0.0 to 1.0)."""
        if not self.tasks:
            return 0.0
        
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        return completed / len(self.tasks)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get todo list summary."""
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        
        return {
            "total_tasks": len(self.tasks),
            "status_counts": status_counts,
            "progress": self.get_progress(),
            "pending_high_priority": len(self.get_pending_tasks(priority_threshold=4))
        }

class AgentCommunicationBridge:
    """
    Enables bidirectional communication between Agent Zero and NanoBot.
    Handles permissions, data exchange, and task coordination.
    """
    
    def __init__(self, agent_zero_endpoint: str, nanobot_endpoint: str):
        self.agent_zero_endpoint = agent_zero_endpoint
        self.nanobot_endpoint = nanobot_endpoint
        self.communication_log: List[Dict] = []
    
    async def send_to_nanobot(self, message: str, permission_required: bool = False) -> Dict:
        """Send message to NanoBot, optionally requesting permission."""
        log_entry = {
            "from": "AgentZero",
            "to": "NanoBot",
            "message": message,
            "permission_required": permission_required,
            "timestamp": datetime.now().isoformat()
        }
        self.communication_log.append(log_entry)
        
        # In production, this would make HTTP call to nanobot endpoint
        # For now, return simulated response
        logger.info(f"Bridge: AgentZero -> NanoBot: {message}")
        return {"status": "sent", "permission_granted": not permission_required}
    
    async def send_to_agent_zero(self, message: str, data: Any = None) -> Dict:
        """Send message/data to Agent Zero."""
        log_entry = {
            "from": "NanoBot",
            "to": "AgentZero",
            "message": message,
            "data": str(data) if data else None,
            "timestamp": datetime.now().isoformat()
        }
        self.communication_log.append(log_entry)
        
        logger.info(f"Bridge: NanoBot -> AgentZero: {message}")
        return {"status": "received"}
    
    async def request_permission(self, action: str, context: Dict) -> bool:
        """Request permission from user for critical actions."""
        # In production, this would trigger UI prompt
        logger.info(f"Permission requested for: {action}")
        return True  # Auto-grant for development
    
    def get_communication_history(self) -> List[Dict]:
        """Get communication history between agents."""
        return self.communication_log

class AutoResearchOrchestrator:
    """
    Orchestrates automatic research workflow.
    Detects topics, plans research, generates todo, executes, stores.
    """
    
    def __init__(
        self,
        surfsense_client=None,
        web_scraper=None,
        communication_bridge: AgentCommunicationBridge = None
    ):
        self.detector = ResearchTopicDetector()
        self.todo_manager = TodoListManager()
        self.bridge = communication_bridge or AgentCommunicationBridge(
            agent_zero_endpoint="/api/agent",
            nanobot_endpoint="/api/nanobot"
        )
        self.surfsense_client = surfsense_client
        self.web_scraper = web_scraper
        
        self.active_research: Optional[ResearchPlan] = None
        self.research_history: List[ResearchPlan] = []
    
    def detect_research_topic(self, message: str) -> Optional[ResearchTopic]:
        """Detect if message contains a research topic."""
        return self.detector.detect(message)
    
    def create_research_plan(self, topic: ResearchTopic) -> ResearchPlan:
        """Create comprehensive research plan based on topic type."""
        self.todo_manager = TodoListManager()  # Reset for new research
        
        stages = self._get_research_stages(topic.research_type)
        tasks = self._generate_research_tasks(topic, stages)
        
        plan = ResearchPlan(
            topic=topic.topic,
            research_type=topic.research_type,
            stages=stages,
            tasks=tasks
        )
        
        self.active_research = plan
        logger.info(f"Created research plan for: {topic.topic}")
        return plan
    
    def _get_research_stages(self, research_type: str) -> Dict[str, List[str]]:
        """Get research stages based on type."""
        base_stages = {
            "planning": [
                "Define research questions",
                "Identify search terms",
                "Select databases",
                "Define inclusion/exclusion criteria"
            ],
            "deep_research": [
                "Literature search",
                "Abstract screening",
                "Full-text review",
                "Data extraction"
            ],
            "web_scraping": [
                "Identify target websites",
                "Extract structured data",
                "Verify data quality"
            ],
            "analysis": [
                "Statistical analysis",
                "Meta-analysis (if applicable)",
                "Synthesis of findings"
            ],
            "storage": [
                "Upload to SurfSense",
                "Create knowledge graph",
                "Generate report"
            ]
        }
        
        # Add stages for specific research types
        if research_type == "phd":
            base_stages["planning"].extend([
                "Develop theoretical framework",
                "Design methodology",
                "Plan data collection"
            ])
        elif research_type == "grand":
            base_stages["planning"].extend([
                "Define multi-center protocol",
                "Plan collaborative workflow",
                "Establish data sharing agreements"
            ])
        elif research_type == "review_article":
            base_stages["planning"].extend([
                "Register review protocol",
                "Define PRISMA guidelines",
                "Plan search strategy"
            ])
        
        return base_stages
    
    def _generate_research_tasks(self, topic: ResearchTopic, stages: Dict) -> List[ResearchTask]:
        """Generate todo list tasks from research stages."""
        tasks = []
        prev_task_id = None
        
        priority_map = {
            "planning": 5,
            "deep_research": 5,
            "web_scraping": 4,
            "analysis": 5,
            "storage": 3
        }
        
        for stage_name, stage_items in stages.items():
            for item in stage_items:
                task = self.todo_manager.create_task(
                    title=f"[{stage_name.upper()}] {item}",
                    description=f"Execute: {item} for research on '{topic.topic}'",
                    priority=priority_map.get(stage_name, 3),
                    dependencies=[prev_task_id] if prev_task_id else None
                )
                tasks.append(task)
                prev_task_id = task.id
        
        return tasks
    
    async def execute_research(self, plan: ResearchPlan) -> ResearchPlan:
        """Execute research plan automatically."""
        plan.current_stage = ResearchStage.PLANNING
        
        # Notify NanoBot about research start
        await self.bridge.send_to_nanobot(
            f"Starting research on: {plan.topic}",
            permission_required=True
        )
        
        try:
            # Execute tasks in priority order
            while True:
                pending = self.todo_manager.get_pending_tasks()
                if not pending:
                    break
                
                for task in pending:
                    plan.current_stage = self._get_stage_from_task(task.title)
                    
                    # Execute task
                    result = await self._execute_task(task)
                    self.todo_manager.update_task_status(
                        task.id, "completed" if result["success"] else "failed",
                        result.get("message")
                    )
                    
                    plan.progress = self.todo_manager.get_progress()
                    
                    # Notify Agent Zero about progress
                    await self.bridge.send_to_agent_zero(
                        f"Task completed: {task.title}",
                        {"progress": plan.progress}
                    )
            
            plan.current_stage = ResearchStage.COMPLETED
            self.research_history.append(plan)
            
        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            plan.current_stage = ResearchStage.FAILED
        
        return plan
    
    async def _execute_task(self, task: ResearchTask) -> Dict[str, Any]:
        """Execute a single research task."""
        logger.info(f"Executing task: {task.title}")
        
        # In production, this would route to appropriate handlers
        # For now, simulate execution
        await asyncio.sleep(0.1)  # Simulate work
        
        return {
            "success": True,
            "message": f"Task {task.id} completed successfully"
        }
    
    def _get_stage_from_task(self, task_title: str) -> ResearchStage:
        """Determine research stage from task title."""
        if "[PLANNING]" in task_title:
            return ResearchStage.PLANNING
        elif "[DEEP_RESEARCH]" in task_title:
            return ResearchStage.DEEP_RESEARCH
        elif "[WEB_SCRAPING]" in task_title:
            return ResearchStage.WEB_SCRAPING
        elif "[ANALYSIS]" in task_title:
            return ResearchStage.ANALYSIS
        elif "[STORAGE]" in task_title:
            return ResearchStage.STORAGE
        return ResearchStage.DETECTED
