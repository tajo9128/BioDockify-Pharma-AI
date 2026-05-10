"""
MonitoredAgentZero - Prometheus-instrumented wrapper for Agent Zero Hybrid Agent.
Preserves self-repair and self-diagnosis features while adding observability.
"""

import time
import logging
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram

from agent_zero.hybrid.agent import HybridAgent
from agent_zero.hybrid.context import AgentConfig
from orchestration.planner.orchestrator import OrchestratorConfig
# We assume SelfRepairSkill is a standard skill accessible via the agent or separately
# For monitoring, we wrap the execute calls.

logger = logging.getLogger("BioDockify.MonitoredAgent")

class MonitoredAgentZero:
    """
    Agent Zero with self-repair + Prometheus monitoring.
    """
    
    def __init__(self, agent_config: AgentConfig, llm_config: OrchestratorConfig):
        # Keep original Agent Zero
        self.agent = HybridAgent(
            config=agent_config,
            llm_config=llm_config
        )
        
        # Setup metrics
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        try:
            # Total executions by status (success/failed) and mode
            self.execution_counter = Counter(
                'agent_zero_executions_total',
                'Total agent executions',
                ['status', 'mode']
            )
            
            # Duration of executions
            self.execution_duration = Histogram(
                'agent_zero_execution_duration_seconds',
                'Agent execution duration',
                ['mode', 'self_repair_used']
            )
            
            # Self-repair attempts and success
            self.repair_counter = Counter(
                'agent_zero_self_repairs_total',
                'Total self-repair attempts',
                ['success', 'repair_type']
            )
            
            # Error diagnoses
            self.diagnosis_counter = Counter(
                'agent_zero_diagnoses_total',
                'Total error diagnoses',
                ['error_type']
            )
        except ValueError:
             # Metrics already registered
            from prometheus_client import REGISTRY
            self.execution_counter = REGISTRY._names_to_collectors['agent_zero_executions_total']
            self.execution_duration = REGISTRY._names_to_collectors['agent_zero_execution_duration_seconds']
            self.repair_counter = REGISTRY._names_to_collectors['agent_zero_self_repairs_total']
            self.diagnosis_counter = REGISTRY._names_to_collectors['agent_zero_diagnoses_total']

    async def execute(self, task: str, mode: str = 'standard') -> Dict[str, Any]:
        """
        Execute task with monitoring + self-repair + Sentry breadcrumbs.
        """
        start_time = time.time()
        
        if sentry_sdk:
            sentry_sdk.add_breadcrumb(
                category='agent_zero',
                message=f"Executing task: {task[:100]}",
                level='info'
            )
        
        try:
            # Execute with Agent Zero
            # HybridAgent.execute already handles self-repair if enabled in config
            result = await self.agent.execute(task)
            
            duration = time.time() - start_time
            self.execution_counter.labels(status='success', mode=mode).inc()
            
            # Use labels for duration histogram if they exist
            self.execution_duration.labels(
                mode=mode, 
                self_repair_used=str(result.get("self_repair_used", False)).lower()
            ).observe(duration)
            
            # Record self-repair metrics if found in result
            if result.get("self_repair_used"):
                self.repair_counter.labels(
                    success="true",
                    repair_type=result.get("repair_type", "unknown")
                ).inc()
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.execution_counter.labels(status='error', mode=mode).inc()
            
            # Capture exception with Sentry
            if sentry_sdk:
                sentry_sdk.capture_exception(e)
            
            # Record diagnosis metrics
            self.diagnosis_counter.labels(error_type=type(e).__name__).inc()
            
            logger.error(f"Agent Zero Execution Failed: {e}")
            raise
            
    async def initialize(self):
        """Initialize the underlying agent."""
        if hasattr(self.agent, "initialize"):
             await self.agent.initialize()
             
    async def stop(self):
        """Stop agent and clean up."""
        if hasattr(self.agent, "stop"):
             await self.agent.stop()
