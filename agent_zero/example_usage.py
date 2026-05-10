"""
Agent Zero Integration Example

This example demonstrates how to use the complete Agent Zero system:
- LLMProvider: For text generation
- ToolRegistry: For managing research tools
- PersistentMemory: For storing and recalling memories
- PhDPlanner: For stage detection and tool recommendation
- AgentZero: The main orchestrator
"""

import asyncio
from datetime import datetime
from typing import Dict, List


# Mock implementations for demonstration
class MockLLMProvider:
    """Mock LLM provider for testing"""

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock responses"""
        # In production, this would call an actual LLM API
        return "Example response"


class MockTool:
    """Mock tool for demonstration"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def execute(self, params: Dict) -> Dict:
        """Execute mock tool"""
        return {
            'success': True,
            'data': f"Executed {self.name} with params: {params}",
            'timestamp': datetime.now().isoformat()
        }


async def main():
    """Main integration example"""

    # ============================================================================
    # 1. Initialize Components
    # ============================================================================

    from agent_zero.core.orchestrator import AgentZero, ToolRegistry, LLMProvider
    from agent_zero.core.planner import PhDPlanner
    from agent_zero.core.memory import PersistentMemory

    print("=" * 60)
    print("Agent Zero Integration Example")
    print("=" * 60)
    print()

    # Initialize LLM provider
    print("Step 1: Initializing LLM Provider...")
    llm = MockLLMProvider()
    print("✓ LLM Provider initialized")
    print()

    # Initialize tool registry
    print("Step 2: Setting up Tool Registry...")
    tool_registry = ToolRegistry()

    # Register some mock tools
    tools = [
        MockTool('literature_landscape', 'Analyze literature landscape'),
        MockTool('gap_detection', 'Detect research gaps'),
        MockTool('novelty_scoring', 'Score research novelty'),
        MockTool('literature_review', 'Conduct literature review'),
        MockTool('hypothesis_generation', 'Generate hypotheses'),
        MockTool('docking_execution', 'Execute molecular docking'),
        MockTool('data_synthesis', 'Synthesize research data'),
    ]

    for tool in tools:
        tool_registry.register(tool)

    print(f"✓ Registered {len(tools)} tools")
    print()

    # Initialize memory store
    print("Step 3: Initializing Persistent Memory...")
    memory = PersistentMemory('./data/agent_memory')
    print("✓ Memory store initialized")
    print()

    # Initialize planner
    print("Step 4: Initializing PhD Planner...")
    planner = PhDPlanner(llm)
    print("✓ PhD Planner initialized")
    print()

    # Initialize Agent Zero
    print("Step 5: Initializing Agent Zero...")
    agent = AgentZero(llm, tool_registry, memory, max_retries=3)
    print("✓ Agent Zero initialized")
    print()

    # ============================================================================
    # 2. Detect PhD Stage
    # ============================================================================

    print("=" * 60)
    print("Detecting PhD Stage")
    print("=" * 60)
    print()

    # Example 1: Detect from milestones
    project_metadata = {
        'literature_review_complete': True,
        'experiments_started': False,
        'experiments_complete': False,
        'thesis_started': False
    }

    stage = planner.detect_phd_stage(project_metadata)
    print(f"Detected stage from milestones: {stage}")
    print(f"Stage description: {planner.get_stage_description(stage)}")
    print()

    # Example 2: Detect from timeline
    start_date = "2023-06-01"
    stage = planner.detect_phd_stage_from_timeline(start_date, total_duration_years=4)
    print(f"Detected stage from timeline (started {start_date}): {stage}")
    print()

    # ============================================================================
    # 3. Recommend Tools
    # ============================================================================

    print("=" * 60)
    print("Tool Recommendation")
    print("=" * 60)
    print()

    goal = "Conduct comprehensive literature review on Alzheimer's drug targets"
    stage = "early"

    print(f"Goal: {goal}")
    print(f"Stage: {stage}")
    print()

    # Simple recommendation
    print("Simple recommendations (keyword-based):")
    recommended = planner.recommend_tools_simple(
        goal, stage, tool_registry.get_tool_names()
    )
    for tool in recommended:
        print(f"  - {tool}")
    print()

    # ============================================================================
    # 4. Memory Operations
    # ============================================================================

    print("=" * 60)
    print("Memory Operations")
    print("=" * 60)
    print()

    # Store some memories
    print("Storing sample memories...")
    await memory.store({
        'task': {'task': 'literature_review', 'params': {'topic': 'Alzheimer'}},
        'result': {'success': True, 'papers_found': 45},
        'goal': 'Initial literature survey',
        'phd_stage': 'proposal'
    }, tags=['literature', 'alzheimer'])

    await memory.store({
        'task': {'task': 'gap_detection', 'params': {'domain': 'drug_targets'}},
        'result': {'success': True, 'gaps_found': 3},
        'goal': 'Identify research gaps',
        'phd_stage': 'proposal'
    }, tags=['gaps', 'analysis'])

    await memory.store({
        'task': {'task': 'hypothesis_generation', 'params': {}},
        'result': {'success': True, 'hypotheses': ['H1', 'H2']},
        'goal': 'Generate testable hypotheses',
        'phd_stage': 'early'
    }, tags=['hypotheses'])

    print(f"✓ Stored 3 sample memories")
    print()

    # Recall memories
    print("Recalling memories for 'Alzheimer':")
    recalled = memory.recall('Alzheimer', limit=5)
    for mem in recalled:
        print(f"  - Task: {mem.get('task', {}).get('task')}")
        print(f"    Goal: {mem.get('goal')}")
        print(f"    Time: {mem.get('timestamp')[:19]}")
    print()

    # Get statistics
    print("Memory statistics:")
    stats = memory.get_statistics()
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Successful tasks: {stats['successful_tasks']}")
    print(f"  Failed tasks: {stats['failed_tasks']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Stage distribution: {stats['stage_distribution']}")
    print()

    # ============================================================================
    # 5. Get Context
    # ============================================================================

    print("=" * 60)
    print("Context Generation")
    print("=" * 60)
    print()

    stage = 'proposal'
    context = memory.get_context(stage, max_memories=5)
    print(f"Context for stage '{stage}':")
    print(context)
    print()

    # ============================================================================
    # 6. Agent Zero Execution
    # ============================================================================

    print("=" * 60)
    print("Agent Zero Execution")
    print("=" * 60)
    print()

    goal = "Analyze drug targets for Alzheimer's disease"
    stage = "early"

    print(f"Goal: {goal}")
    print(f"Stage: {stage}")
    print()
    print("Executing... (this would normally take time)")
    print()

    # Note: In a real implementation, you would execute:
    # result = await agent.execute_goal(goal, stage)
    # print(f"Success: {result['success']}")
    # print(f"Tasks completed: {result['successful_tasks']}/{result['total_tasks']}")
    # print(f"Execution time: {result['execution_time']:.2f}s")
    # print(f"Thinking steps: {len(result['thinking'])}")

    # For this example, we'll simulate the result structure
    result = {
        'success': True,
        'results': [
            {'success': True, 'data': 'Task 1 complete'},
            {'success': True, 'data': 'Task 2 complete'},
        ],
        'thinking': [
            {'step': 'decomposition', 'goal': goal},
            {'step': 'execution', 'status': 'complete'}
        ],
        'execution_time': 15.5,
        'successful_tasks': 2,
        'failed_tasks': 0,
        'total_tasks': 2
    }

    print(f"Success: {result['success']}")
    print(f"Tasks completed: {result['successful_tasks']}/{result['total_tasks']}")
    print(f"Execution time: {result['execution_time']:.2f}s")
    print(f"Thinking steps: {len(result['thinking'])}")
    print()

    # ============================================================================
    # 7. Recent Activities
    # ============================================================================

    print("=" * 60)
    print("Recent Activities")
    print("=" * 60)
    print()

    activities = memory.get_recent_activities(limit=5)
    for idx, activity in enumerate(activities, 1):
        print(f"{idx}. Task: {activity['task']}")
        print(f"   Goal: {activity['goal']}")
        print(f"   Stage: {activity['stage']}")
        print(f"   Success: {activity['success']}")
        print(f"   Time: {activity['timestamp'][:19]}")
        print()

    # ============================================================================
    # 8. Export/Import
    # ============================================================================

    print("=" * 60)
    print("Export/Import")
    print("=" * 60)
    print()

    print("Exporting memories...")
    export_path = memory.export_memories()
    print(f"✓ Exported to: {export_path}")
    print()

    # ============================================================================
    # Summary
    # ============================================================================

    print("=" * 60)
    print("Integration Example Complete")
    print("=" * 60)
    print()
    print("Summary of demonstrated features:")
    print("  ✓ LLM Provider initialization")
    print("  ✓ Tool Registry setup and tool registration")
    print("  ✓ Persistent Memory store")
    print("  ✓ PhD Planner for stage detection")
    print("  ✓ Agent Zero orchestrator")
    print("  ✓ PhD stage detection (from milestones and timeline)")
    print("  ✓ Tool recommendation")
    print("  ✓ Memory storage and retrieval")
    print("  ✓ Memory statistics")
    print("  ✓ Context generation")
    print("  ✓ Recent activities tracking")
    print("  ✓ Memory export")
    print()


# Additional usage examples
def example_planner_usage():
    """Demonstrate planner usage"""

    from agent_zero.core.planner import PhDPlanner, MockLLMProvider

    planner = PhDPlanner(MockLLMProvider())

    # Get all stages
    print("Available PhD stages:")
    for stage in planner.get_all_stages():
        print(f"  - {stage}: {planner.get_stage_tools(stage)[:3]}")
    print()

    # Get stage progression
    progression = planner.get_stage_progression()
    print("Stage progression order:")
    for stage, order in sorted(progression.items(), key=lambda x: x[1]):
        print(f"  {order}. {stage}")
    print()


def example_memory_usage():
    """Demonstrate memory usage"""

    from agent_zero.core.memory import PersistentMemory

    memory = PersistentMemory('./data/agent_memory')

    # Store with tags
    asyncio.run(memory.store({
        'task': {'task': 'example_task'},
        'result': {'success': True},
        'goal': 'Example goal',
        'phd_stage': 'early'
    }, tags=['example', 'test']))

    # Search by tags
    results = memory.recall('example', limit=5)
    print(f"Found {len(results)} memories with tag 'example'")
    print()

    # Recall by stage
    stage_memories = memory.recall_by_stage('early', limit=10)
    print(f"Found {len(stage_memories)} memories from 'early' stage")
    print()

    # Recall by task
    task_memories = memory.recall_by_task('example_task', limit=5)
    print(f"Found {len(task_memories)} memories for 'example_task'")
    print()


if __name__ == '__main__':
    # Run main example
    asyncio.run(main())

    print("\n" + "=" * 60)
    print("Additional Examples")
    print("=" * 60 + "\n")

    # Run additional examples
    example_planner_usage()
    example_memory_usage()
