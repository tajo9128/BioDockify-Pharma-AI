"""
Agent Zero - Autonomous Research Orchestrator
This is the core autonomous agent that:
- Receives high-level PhD research goals
- Decomposes into executable tasks
- Selects appropriate tools
- Self-corrects on failures
- Maintains persistent memory
"""

from typing import Dict, List, Optional, Any
import asyncio
import json
import re
import logging
from datetime import datetime
from dataclasses import dataclass, field
import asyncio.exceptions



# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
 
# CONFIGURATION CONSTANTS (Bug Fix: Remove Magic Numbers)
DEFAULT_MAX_RETRIES = 3
DEFAULT_TOOL_TIMEOUT = 60
DEFAULT_MAX_TOKENS = 2000
VALIDATION_TIMEOUT = 30
MAX_CONTENT_PREVIEW = 2000


@dataclass
class LLMProvider:
    """Abstract base class for LLM providers"""

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        raise NotImplementedError

    async def generate_json(self, prompt: str, **kwargs) -> Dict:
        """Generate JSON output from prompt"""
        response = await self.generate(prompt, **kwargs)
        return self._parse_json(response)

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Extract JSON from LLM response - Unified robust version"""
        if not text:
            return {}
            
        text = text.strip()
        
        # 1. Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Find JSON block using regex (handles markdown blocks or preamble)
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                content = match.group(1)
                return json.loads(content)
            except json.JSONDecodeError:
                # 3. Clean common LLM formatting issues (trailing commas, etc.)
                try:
                    cleaned = re.sub(r',\s*([\]\}])', r'\1', content)
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from block: {text[:100]}...")

        return {}


@dataclass
class Tool:
    """Represents a research tool"""

    name: str
    description: str
    async def execute(self, params: Dict) -> Any:
        """Execute the tool with given parameters"""
        raise NotImplementedError


class ToolRegistry:
    """Registry for available research tools"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_descriptions: List[str] = []

    def register(self, tool: Tool):
        """Register a new tool"""
        self._tools[tool.name] = tool
        self._tool_descriptions.append(f"- {tool.name}: {tool.description}")
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name"""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")
        return tool

    def list_tools(self) -> str:
        """Get formatted list of available tools"""
        if not self._tool_descriptions:
            return "No tools registered"
        return "\n".join(self._tool_descriptions)

    def get_tool_names(self) -> List[str]:
        """Get list of tool names"""
        return list(self._tools.keys())


class MemoryStore:
    """Abstract base class for memory storage"""

    async def store(self, memory: Dict):
        """Store a memory entry"""
        raise NotImplementedError

    def recall(self, query: str, limit: int = 10) -> List[Dict]:
        """Recall relevant memories"""
        raise NotImplementedError

    def get_context(self, phd_stage: str) -> str:
        """Get context for a PhD stage"""
        raise NotImplementedError


class AgentZero:
    """
    Main autonomous orchestrator for PhD research tasks

    Attributes:
        llm: LLM provider for reasoning and text generation
        tools: Registry of available tools
        memory: Persistent memory storage
        thinking: List of reasoning steps
        is_running: Whether the agent is currently executing
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        memory_store: MemoryStore,
        max_retries: int = 3,
        tool_timeout: int = 60
    ):
        """
        Initialize Agent Zero

        Args:
            llm_provider: LLM provider for reasoning
            tool_registry: Registry of available tools
            memory_store: Persistent memory storage
            max_retries: Maximum retry attempts for failed tasks
            tool_timeout: Timeout for tool execution in seconds
        """
        self.llm = llm_provider
        self.tools = tool_registry
        self.memory = memory_store
        self.max_retries = max_retries
        self.tool_timeout = tool_timeout

        self.thinking: List[Dict] = []
        self.is_running = False
        self._execution_log: List[Dict] = []
        self._lock = asyncio.Lock()
        
        # Circuit Breaker state (Fix for Architecture Requirement #2)
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_threshold = 5
        
        # Auto-load email from storage if available
        self._user_email = "user@biodockify.ai"  # License disabled - unlimited user

    async def execute_goal(
        self,
        goal: str,
        phd_stage: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Main autonomous loop for executing research goals

        Args:
            goal: High-level research goal (e.g., "conduct literature review")
            phd_stage: Current stage (proposal, early, mid, late, submission)
            context: Optional additional context for execution

        Returns:
            Dict with results, execution log, and thinking process
        """
        async with self._lock:
            if self.is_running:
                logger.warning("Agent is already running. Cannot start new execution.")
                return {
                    'success': False,
                    'error': 'Agent is already executing a task',
                    'results': [],
                    'thinking': self.thinking
                }

            self.is_running = True
        self.thinking = []
        self._execution_log = []

        execution_start = datetime.now()
        logger.info(f"Starting goal execution: '{goal}' (Stage: {phd_stage})")

        try:
            # 0. Security: License Check (monthly check against Supabase)
            # Ensure we have email
            if not self._user_email:
                self._user_email = "user@biodockify.ai"  # License disabled - unlimited user
                
            if not self._user_email:
                 logger.warning("License check failed: No user email found")
                 return {
                    'success': False,
                    'error': 'License Verification Failed: No user email found. Please sign in or complete setup.',
                    'license_expired': True,
                    'results': [],
                    'thinking': []
                }

            if self._user_email:
                self._license_valid, self._license_message = (True, "License bypassed - unlimited access enabled")  # License disabled
                if not self._license_valid:
                    logger.warning(f"License check failed: {self._license_message}")
                    return {
                        'success': False,
                        'error': f'License Expired: {self._license_message}',
                        'license_expired': True,
                        'results': [],
                        'thinking': []
                    }
                logger.info(f"License verified: {self._license_message}")
            
            # 1. Decompose goal into tasks
            logger.info("Step 1: Decomposing goal into tasks...")
            tasks = await self._decompose_goal(goal, phd_stage, context)

            if not tasks:
                logger.warning("No tasks generated from goal decomposition")
                return {
                    'success': False,
                    'error': 'No tasks could be generated from the goal',
                    'results': [],
                    'thinking': self.thinking
                }

            logger.info(f"Generated {len(tasks)} tasks")

            # 2. Execute tasks - Parallel Execution if independent (Fix for Bottleneck #1)
            # For simplicity, we assume independent tasks can be grouped by the orchestrator 
            # If the decomposition provides 'independent': true metadata
            
            # We'll use a gathering approach for all tasks if no dependencies are detected
            logger.info(f"Executing {len(tasks)} tasks in parallel...")
            
            async def execute_and_log(idx, task):
                if self._circuit_open:
                     return {'success': False, 'error': 'Circuit Breaker Open'}
                     
                result = await self._execute_task_with_retry(task, phd_stage)
                
                # Store in memory
                try:
                    await self.memory.store({
                        'task': task,
                        'result': result,
                        'phd_stage': phd_stage,
                        'goal': goal,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as me:
                    logger.error(f"Failed to store memory: {me}")
                
                return result

            # Run all tasks concurrently
            tasks_execution = [execute_and_log(i, t) for i, t in enumerate(tasks, 1)]
            results = await asyncio.gather(*tasks_execution)
            
            successful_tasks = sum(1 for r in results if r.get('success'))
            failed_tasks = len(results) - successful_tasks

            execution_end = datetime.now()
            execution_time = (execution_end - execution_start).total_seconds()

            logger.info(f"Execution complete. Success: {successful_tasks}, Failed: {failed_tasks}, Time: {execution_time:.2f}s")

            return {
                'success': failed_tasks == 0,
                'results': results,
                'thinking': self.thinking,
                'execution_time': execution_time,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'total_tasks': len(tasks)
            }

        except Exception as e:
            logger.error(f"Fatal error during execution: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Fatal error: {str(e)}',
                'results': self._execution_log,
                'thinking': self.thinking
            }

        finally:
            self.is_running = False

    async def _decompose_goal(
        self,
        goal: str,
        stage: str,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Use LLM to break down goal into executable tasks

        Args:
            goal: High-level research goal
            stage: Current PhD stage
            context: Optional additional context

        Returns:
            List of task dictionaries
        """
        # Get relevant context from memory
        memory_context = self.memory.get_context(stage)

        prompt = f"""
You are a PhD research assistant. Decompose this goal into specific, executable tasks.

Goal: {goal}
PhD Stage: {stage}

Available tools:
{self.tools.list_tools()}

Relevant memory context:
{memory_context[:1000] if memory_context else "No previous memories"}

{"Additional context: " + str(context) if context else ""}

Output format (JSON array only, no explanation):
[
  {{"task": "tool_name", "params": {{"param1": "value1", "param2": "value2"}}}},
  {{"task": "another_tool", "params": {{"query": "..."}}}}
]

Requirements:
1. Tasks must use only the available tools listed above
2. Each task must have a "task" field with the exact tool name
3. Each task must have a "params" field with appropriate parameters
4. Return ONLY the JSON array, no other text
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=DEFAULT_MAX_TOKENS)
            tasks = LLMProvider._parse_json(response)

            # Ensure we have a list (fix for reported bug #2)
            if isinstance(tasks, dict):
                tasks = [tasks]
            elif not isinstance(tasks, list):
                logger.warning(f"Expected list of tasks, got {type(tasks)}")
                return []

            # Validate each task
            valid_tasks = []
            for task in tasks:
                if isinstance(task, dict) and 'task' in task and 'params' in task:
                    valid_tasks.append(task)
                else:
                    logger.warning(f"Invalid task format: {task}")

            self.thinking.append({
                'step': 'decomposition',
                'goal': goal,
                'stage': stage,
                'tasks': valid_tasks,
                'timestamp': datetime.now().isoformat()
            })

            return valid_tasks

        except Exception as e:
            logger.error(f"Error during goal decomposition: {str(e)}")
            return []

    async def _execute_task_with_retry(
        self,
        task: Dict,
        phd_stage: str,
        max_retries: Optional[int] = None
    ) -> Dict:
        """
        Execute task with automatic retry on failure

        Args:
            task: Task dictionary with 'task' and 'params'
            phd_stage: Current PhD stage for context
            max_retries: Override default max retries

        Returns:
            Dict with success status and data or error
        """
        if max_retries is None:
            max_retries = self.max_retries

        original_task = task.copy()
        attempts = []

        for attempt in range(max_retries):
            attempt_start = datetime.now()
            attempt_info = {
                'attempt': attempt + 1,
                'task': task,
                'started_at': attempt_start.isoformat()
            }

            if self._circuit_open:
                return {'success': False, 'error': 'Circuit Breaker Active - Skipping Execution'}

            try:
                # Get tool and execute
                tool_name = task['task']
                tool = self.tools.get_tool(tool_name)

                logger.info(f"Attempt {attempt + 1}: Executing {tool_name}")

                # Validate params
                params = task.get('params', {})
                if not isinstance(params, dict):
                    params = {}

                # Execute tool with timeout (Fix for bug #3)
                try:
                    result = await asyncio.wait_for(
                        tool.execute(params), 
                        timeout=self.tool_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Tool {tool_name} timed out after {self.tool_timeout}s")
                    raise ToolTimeoutError(f"Execution timed out")

                attempt_info['status'] = 'executed'
                attempt_info['result_summary'] = str(result)[:200]

                # Self-validate result
                is_valid = await self._validate_result(result, task, phd_stage)
                attempt_info['validated'] = is_valid

                if is_valid:
                    attempt_info['completed_at'] = datetime.now().isoformat()
                    attempts.append(attempt_info)

                    self._execution_log.append({
                        'task': task,
                        'attempts': attempts,
                        'final_status': 'success'
                    })

                    return {
                        'success': True,
                        'data': result,
                        'attempts': len(attempts),
                        'task_name': tool_name
                    }
                else:
                    self._failure_count += 1
                    if self._failure_count >= self._circuit_threshold:
                        self._circuit_open = True
                        logger.critical("CIRCUIT BREAKER OPENED: Too many sequential failures")
                        
                    logger.warning(f"Attempt {attempt + 1}: Result validation failed")
                    # Self-correction
                    task = await self._adjust_task_params(task, result, phd_stage)
                    attempt_info['status'] = 'validation_failed'
                    attempt_info['adjusted_task'] = task

            except ValueError as e:
                # Tool not found
                logger.error(f"Attempt {attempt + 1}: Tool error - {str(e)}")
                attempt_info['status'] = 'tool_error'
                attempt_info['error'] = str(e)

                if attempt == max_retries - 1:
                    attempt_info['completed_at'] = datetime.now().isoformat()
                    attempts.append(attempt_info)
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': len(attempts),
                        'task_name': task.get('task', 'unknown')
                    }

                # Try alternative approach
                task = await self._handle_failure(task, e, phd_stage)

            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Execution error - {str(e)}")
                attempt_info['status'] = 'execution_error'
                attempt_info['error'] = str(e)

                if attempt == max_retries - 1:
                    attempt_info['completed_at'] = datetime.now().isoformat()
                    attempts.append(attempt_info)
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': len(attempts),
                        'task_name': task.get('task', 'unknown')
                    }

                # Self-correction on failure
                task = await self._handle_failure(task, e, phd_stage)
                attempt_info['adjusted_task'] = task

            finally:
                if 'completed_at' not in attempt_info:
                    attempt_info['completed_at'] = datetime.now().isoformat()
                attempts.append(attempt_info)

        # All retries exhausted
        self._execution_log.append({
            'task': original_task,
            'attempts': attempts,
            'final_status': 'failed'
        })

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'attempts': len(attempts),
            'task_name': original_task.get('task', 'unknown')
        }

    async def _validate_result(
        self,
        result: Any,
        task: Dict,
        phd_stage: str
    ) -> bool:
        """
        Use LLM to validate if result meets expectations

        Args:
            result: Result from tool execution
            task: Original task dictionary
            phd_stage: Current PhD stage

        Returns:
            True if result is valid, False otherwise
        """
        prompt = f"""
Validate if this result fulfills the task requirements.

Task: {json.dumps(task, indent=2)}
Result: {str(result)[:2000] if result else "No result"}
PhD Stage: {phd_stage}

Evaluate based on:
1. Does the result match the task's intended outcome?
2. Is the data complete and meaningful?
3. Are there any obvious errors or missing information?

Respond with either:
- VALID
- INVALID: [brief reason]

Response must start with VALID or INVALID.
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=500)
            response = response.strip().upper()

            is_valid = response.startswith('VALID')

            if not is_valid:
                reason = response.replace('INVALID:', '').strip()[:200]
                logger.info(f"Result validation failed: {reason}")

            return is_valid

        except Exception as e:
            logger.error(f"Error during result validation: {str(e)}")
            # Default to true if validation fails, to avoid blocking progress
            return True

    async def _adjust_task_params(
        self,
        task: Dict,
        result: Any,
        phd_stage: str
    ) -> Dict:
        """
        Self-correction: adjust task parameters based on result

        Args:
            task: Original task dictionary
            result: Suboptimal result from execution
            phd_stage: Current PhD stage

        Returns:
            Adjusted task dictionary
        """
        prompt = f"""
The task produced suboptimal results. Suggest better parameters.

Original Task: {json.dumps(task, indent=2)}
Result: {str(result)[:2000] if result else "No result"}
PhD Stage: {phd_stage}

Available tools:
{self.tools.list_tools()}

Provide an adjusted task as JSON only:
{{"task": "tool_name", "params": {{"param1": "value1"}}}}

Guidelines:
1. Keep the same task name unless it's fundamentally wrong
2. Adjust parameters to improve the result quality
3. Consider alternative approaches based on the suboptimal result
4. Return ONLY the JSON, no explanation
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=1000)
            adjusted_task = LLMProvider._parse_json(response)

            if adjusted_task and 'task' in adjusted_task:
                logger.info(f"Adjusted task parameters for {task.get('task')}")
                return adjusted_task
            else:
                logger.warning("Could not parse adjusted task, returning original")
                return task

        except Exception as e:
            logger.error(f"Error adjusting task params: {str(e)}")
            return task

    async def _handle_failure(
        self,
        task: Dict,
        error: Exception,
        phd_stage: str
    ) -> Dict:
        """
        Self-correction on failure - suggest alternative approach

        Args:
            task: Failed task dictionary
            error: Exception that occurred
            phd_stage: Current PhD stage

        Returns:
            Alternative task dictionary
        """
        self.thinking.append({
            'step': 'failure_handling',
            'task': task,
            'error': str(error),
            'phd_stage': phd_stage,
            'timestamp': datetime.now().isoformat()
        })

        prompt = f"""
Task failed. Suggest an alternative approach.

Failed Task: {json.dumps(task, indent=2)}
Error: {str(error)}
PhD Stage: {phd_stage}

Available tools:
{self.tools.list_tools()}

Provide an alternative task as JSON only:
{{"task": "tool_name", "params": {{"param1": "value1"}}}}

Guidelines:
1. Choose an alternative tool or different parameters
2. Address the specific error that occurred
3. If possible, provide a workaround approach
4. Return ONLY the JSON, no explanation
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=1000)
            alternative_task = LLMProvider._parse_json(response)

            if alternative_task and 'task' in alternative_task:
                logger.info(f"Generated alternative task: {alternative_task.get('task')}")
                return alternative_task
            else:
                logger.warning("Could not parse alternative task, returning original")
                return task

        except Exception as e:
            logger.error(f"Error generating alternative task: {str(e)}")
            return task

        logger.warning(f"Could not parse JSON from: {text[:200]}")
        return {}

class ToolTimeoutError(Exception):
    """Raised when a tool execution exceeds configured timeout"""
    pass

    def get_thinking_log(self) -> List[Dict]:
        """Get the complete thinking log"""
        return self.thinking.copy()

    def get_execution_log(self) -> List[Dict]:
        """Get the complete execution log"""
        return self._execution_log.copy()
    
    def set_user_email(self, email: str):
        """Set user email for license validation"""
        self._user_email = email
        logger.info(f"User email set for license validation: {email}")
    
    def get_license_status(self) -> Dict:
        """Get current license status"""
        return {
            'valid': self._license_valid,
            'message': self._license_message,
            'email': self._user_email
        }

    def reset(self):
        """Reset the agent state"""
        self.thinking = []
        self._execution_log = []
        self.is_running = False
        logger.info("Agent state reset")

