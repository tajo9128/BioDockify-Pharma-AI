# Agent Zero - Autonomous Research Orchestrator

**Version:** 2.0.0

Agent Zero is an autonomous AI orchestrator designed to serve as the brain of BioDockify v2.0.0. It receives high-level PhD research goals, decomposes them into executable tasks, selects appropriate tools, self-corrects on failures, and maintains persistent memory across the research journey.

## Architecture

```
User Goal → Agent Zero → Tool Selection → Execution → Memory → Results
                ↓
         PhD Planner (Stage Detection)
                ↓
         Tool Registry
                ↓
         Persistent Memory
```

### Core Components

1. **Orchestrator** (`orchestrator.py`)
   - Main autonomous execution loop
   - Goal decomposition into tasks
   - Task execution with retry and self-correction
   - Result validation
   - Failure handling

2. **Planner** (`planner.py`)
   - PhD stage detection
   - Tool recommendation
   - Execution planning
   - Multi-step reasoning

3. **Memory** (`memory.py`)
   - Persistent storage across sessions
   - Keyword-based search and recall
   - Context generation by stage
   - Export/import capabilities

## Installation

```bash
# The agent_zero module is included in the BioDockify project
cd agent_zero
```

## Quick Start

### Basic Usage

```python
import asyncio
from agent_zero.core.orchestrator import AgentZero, ToolRegistry
from agent_zero.core.planner import PhDPlanner
from agent_zero.core.memory import PersistentMemory

async def main():
    # Initialize components
    llm = YourLLMProvider()  # Implement LLMProvider interface
    tool_registry = ToolRegistry()
    memory = PersistentMemory('./data/agent_memory')
    planner = PhDPlanner(llm)

    # Register tools
    tool_registry.register(YourTool())
    tool_registry.register(AnotherTool())

    # Initialize Agent Zero
    agent = AgentZero(llm, tool_registry, memory, max_retries=3)

    # Execute a research goal
    result = await agent.execute_goal(
        goal="Conduct literature review on Alzheimer's drug targets",
        phd_stage="early"
    )

    print(f"Success: {result['success']}")
    print(f"Thinking steps: {len(result['thinking'])}")
    print(f"Results: {result['results']}")

asyncio.run(main())
```

## Component Documentation

### 1. Orchestrator

The main autonomous agent that coordinates all operations.

#### Class: `AgentZero`

```python
class AgentZero:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        memory_store: MemoryStore,
        max_retries: int = 3
    )
```

**Parameters:**
- `llm_provider`: LLM provider for reasoning
- `tool_registry`: Registry of available tools
- `memory_store`: Persistent memory storage
- `max_retries`: Maximum retry attempts (default: 3)

**Methods:**

##### `execute_goal(goal, phd_stage, context=None)`

Execute a research goal autonomously.

**Parameters:**
- `goal` (str): High-level research goal
- `phd_stage` (str): Current PhD stage ('proposal', 'early', 'mid', 'late', 'submission')
- `context` (dict, optional): Additional context

**Returns:**
```python
{
    'success': bool,
    'results': List[Dict],
    'thinking': List[Dict],
    'execution_time': float,
    'successful_tasks': int,
    'failed_tasks': int,
    'total_tasks': int
}
```

**Example:**
```python
result = await agent.execute_goal(
    goal="Conduct comprehensive literature review",
    phd_stage="early",
    context={"focus_area": "molecular docking"}
)
```

##### `get_thinking_log()`

Get the complete reasoning log.

```python
thinking = agent.get_thinking_log()
```

##### `get_execution_log()`

Get the complete execution log.

```python
execution_log = agent.get_execution_log()
```

##### `reset()`

Reset the agent state.

```python
agent.reset()
```

#### Class: `ToolRegistry`

Registry for managing available research tools.

**Methods:**

##### `register(tool: Tool)`

Register a new tool.

```python
tool_registry.register(MyTool())
```

##### `get_tool(name: str) -> Tool`

Get a tool by name.

```python
tool = tool_registry.get_tool('literature_review')
```

##### `list_tools() -> str`

Get formatted list of available tools.

```python
tools = tool_registry.list_tools()
print(tools)
```

#### Class: `Tool`

Base class for implementing research tools.

```python
from agent_zero.core.orchestrator import Tool
import asyncio

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of what this tool does"
        )

    async def execute(self, params: dict) -> dict:
        """Execute the tool with given parameters"""
        # Your implementation
        return {
            'success': True,
            'data': {...}
        }
```

### 2. Planner

Handles PhD stage detection and tool recommendations.

#### Class: `PhDPlanner`

```python
class PhDPlanner:
    def __init__(self, llm: LLMProvider)
```

**Methods:**

##### `detect_phd_stage(project_metadata=None) -> str`

Detect current PhD stage from project metadata.

**Parameters:**
- `project_metadata` (dict): Project information including milestones

**Example:**
```python
metadata = {
    'literature_review_complete': True,
    'experiments_started': False,
    'experiments_complete': False,
    'thesis_started': False
}
stage = planner.detect_phd_stage(metadata)
# Returns: 'early'
```

##### `detect_phd_stage_from_timeline(start_date, total_duration_years=4) -> str`

Detect stage based on timeline.

**Example:**
```python
stage = planner.detect_phd_stage_from_timeline(
    start_date="2023-06-01",
    total_duration_years=4
)
```

##### `recommend_tools(goal, stage, available_tools=None, max_recommendations=5) -> List[str]`

Recommend tools for a given goal and stage.

**Example:**
```python
tools = await planner.recommend_tools(
    goal="Conduct literature review",
    stage="early",
    available_tools=['literature_review', 'gap_detection', ...],
    max_recommendations=3
)
```

##### `create_execution_plan(goal, stage, available_tools, context=None) -> Dict`

Create a detailed execution plan.

**Returns:**
```python
{
    'steps': [
        {
            'step': 1,
            'tool': 'tool_name',
            'description': '...',
            'params': {...},
            'estimated_time': 'hours',
            'dependencies': []
        }
    ],
    'overview': '...',
    'estimated_total_time': 'hours',
    'risks': [...],
    'success_criteria': [...]
}
```

### 3. Memory

Persistent memory storage and retrieval.

#### Class: `PersistentMemory`

```python
class PersistentMemory:
    def __init__(
        self,
        storage_path: str = './data/agent_memory',
        max_long_term: int = 10000,
        max_short_term: int = 100
    )
```

**Methods:**

##### `store(memory, tags=None, metadata=None) -> str`

Store a memory entry.

**Example:**
```python
await memory.store(
    memory={
        'task': {'task': 'literature_review', 'params': {...}},
        'result': {'success': True, 'papers_found': 50},
        'goal': 'Initial literature survey',
        'phd_stage': 'proposal'
    },
    tags=['literature', 'alzheimer'],
    metadata={'priority': 'high'}
)
```

##### `recall(query, limit=10, phd_stage=None, since=None) -> List[Dict]`

Search memories by keywords.

**Example:**
```python
results = memory.recall(
    query="Alzheimer drug targets",
    limit=10,
    phd_stage="early"
)
```

##### `recall_by_task(task_name, limit=10) -> List[Dict]`

Recall memories by task name.

**Example:**
```python
results = memory.recall_by_task('literature_review', limit=5)
```

##### `recall_by_stage(phd_stage, limit=50) -> List[Dict]`

Get all memories from a specific stage.

**Example:**
```python
results = memory.recall_by_stage('mid', limit=50)
```

##### `get_context(phd_stage, max_memories=20, include_failed=True) -> str`

Get relevant context for a PhD stage.

**Example:**
```python
context = memory.get_context('early', max_memories=10)
```

##### `get_statistics() -> Dict`

Get memory usage statistics.

**Returns:**
```python
{
    'total_memories': int,
    'successful_tasks': int,
    'failed_tasks': int,
    'success_rate': float,
    'short_term_count': int,
    'stage_distribution': dict,
    'task_distribution': dict,
    'storage_path': str
}
```

##### `export_memories(output_path=None, format='json') -> str`

Export all memories to a file.

**Example:**
```python
path = memory.export_memories('./backups/memory_backup.json')
```

##### `import_memories(input_path, merge=True) -> int`

Import memories from a file.

**Example:**
```python
count = memory.import_memories('./backups/memory_backup.json', merge=True)
```

##### `prune_old_memories(days=365, keep_recent=100) -> int`

Remove old memories.

**Example:**
```python
pruned = memory.prune_old_memories(days=365, keep_recent=100)
```

##### `backup() -> str`

Create a backup of current memories.

```python
backup_path = memory.backup()
```

##### `restore_backup(backup_path) -> int`

Restore memories from a backup.

```python
count = memory.restore_backup(backup_path)
```

## PhD Stages

The system recognizes five PhD stages:

1. **Proposal**
   - Initial stage with literature landscape analysis
   - Research gap detection
   - Novelty scoring

2. **Early**
   - Comprehensive literature review
   - Hypothesis generation
   - Methodology design

3. **Mid**
   - Docking execution
   - MD simulation
   - Result analysis

4. **Late**
   - Data synthesis
   - Discussion writing
   - Limitation analysis

5. **Submission**
   - Chapter assembly
   - Citation formatting
   - Viva preparation

## LLM Provider Interface

To use Agent Zero, you need to implement the `LLMProvider` interface:

```python
from agent_zero.core.orchestrator import LLMProvider

class MyLLMProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        # Call your LLM API here
        response = await your_llm_api_call(prompt, **kwargs)
        return response
```

## Tool Implementation

Create custom tools by extending the `Tool` class:

```python
from agent_zero.core.orchestrator import Tool

class PubMedSearchTool(Tool):
    def __init__(self):
        super().__init__(
            name="search_pubmed",
            description="Search PubMed for research papers"
        )

    async def execute(self, params: dict) -> dict:
        """Execute PubMed search"""
        query = params.get('query', '')
        max_results = params.get('max_results', 50)

        # Implement PubMed search logic
        results = await self._search_pubmed(query, max_results)

        return {
            'success': True,
            'data': {
                'papers': results,
                'count': len(results)
            }
        }

    async def _search_pubmed(self, query, max_results):
        # Your implementation
        pass
```

## Example: Complete Workflow

```python
import asyncio
from agent_zero.core import AgentZero, PhDPlanner, PersistentMemory, ToolRegistry

async def main():
    # Initialize
    llm = MyLLMProvider()
    tool_registry = ToolRegistry()
    memory = PersistentMemory('./data/agent_memory')
    planner = PhDPlanner(llm)

    # Register tools
    tool_registry.register(PubMedSearchTool())
    tool_registry.register(GapDetectionTool())
    tool_registry.register(DockingTool())

    # Create agent
    agent = AgentZero(llm, tool_registry, memory, max_retries=3)

    # Detect stage
    metadata = {
        'literature_review_complete': True,
        'experiments_started': True,
        'experiments_complete': False,
        'thesis_started': False
    }
    stage = planner.detect_phd_stage(metadata)

    # Recommend tools
    goal = "Find novel drug targets for Alzheimer's"
    tools = await planner.recommend_tools(goal, stage)

    # Execute goal
    result = await agent.execute_goal(goal, stage)

    # View results
    if result['success']:
        print(f"Completed {result['successful_tasks']} tasks")
        for r in result['results']:
            print(f"  - {r['task_name']}: {r['success']}")

asyncio.run(main())
```

## Error Handling

Agent Zero includes built-in error handling and self-correction:

1. **Automatic Retry**: Failed tasks are retried up to `max_retries` times
2. **Self-Correction**: Parameters are adjusted based on results
3. **Alternative Approaches**: New strategies are tried on failure
4. **Validation**: Results are validated before acceptance

```python
result = await agent.execute_goal(goal, stage)

if not result['success']:
    print(f"Errors encountered:")
    for thinking in result['thinking']:
        if thinking.get('step') == 'failure_handling':
            print(f"  - {thinking['task']}: {thinking['error']}")
```

## Memory Management

### Automatic Pruning

Memory automatically prunes when limits are reached:
- Short-term: max 100 entries (configurable)
- Long-term: max 10,000 entries (configurable)

### Manual Pruning

```python
# Remove memories older than 1 year, keep 100 most recent
pruned = memory.prune_old_memories(days=365, keep_recent=100)
```

### Backup and Restore

```python
# Create backup
backup_path = memory.backup()

# Restore from backup
memory.restore_backup(backup_path)
```

## Running Examples

```bash
# Run the integration example
cd agent_zero
python example_usage.py
```

## Project Structure

```
agent_zero/
├── core/
│   ├── __init__.py         # Package initialization
│   ├── orchestrator.py     # Main autonomous orchestrator
│   ├── planner.py          # PhD stage detection and planning
│   └── memory.py           # Persistent memory store
├── example_usage.py        # Complete integration example
└── README.md              # This file
```

## API Integration

Agent Zero can be integrated into web APIs:

```python
# FastAPI example
from fastapi import FastAPI

app = FastAPI()

@app.post("/execute")
async def execute_goal(request: dict):
    goal = request['goal']
    stage = request['phd_stage']

    result = await agent.execute_goal(goal, stage)
    return result

@app.get("/statistics")
async def get_statistics():
    return memory.get_statistics()

@app.get("/stages")
async def get_stages():
    return {
        'current_stage': planner.detect_phd_stage(),
        'all_stages': planner.get_all_stages()
    }
```

## Best Practices

1. **Define Clear Goals**: Be specific about what you want to achieve
2. **Choose Appropriate Stage**: Ensure the PhD stage is correctly set
3. **Implement Robust Tools**: Handle errors gracefully in tool implementations
4. **Use Memory Wisely**: Store important results with descriptive tags
5. **Monitor Execution**: Check thinking and execution logs for insights
6. **Regular Backups**: Export memory regularly for safety
7. **Validate Results**: Use the built-in validation to ensure quality

## Troubleshooting

### Agent not executing tasks

- Check if `is_running` is already True
- Verify tools are properly registered
- Ensure task parameters match tool expectations

### Memory not persisting

- Check write permissions to storage path
- Verify disk space is available
- Check logs for I/O errors

### Poor recommendations

- Ensure LLM provider is configured correctly
- Provide clear, specific goals
- Verify stage detection is accurate

## License

BioDockify v2.0.0 - Agent Zero Module

## Version History

- **2.0.0** (Current): Complete rewrite with async/await, improved memory, and enhanced planning
- Previous versions: Legacy implementations

## Support

For issues and questions, please refer to the main BioDockify documentation.
