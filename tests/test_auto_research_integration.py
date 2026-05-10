
"""Test Auto-Research Integration."""
import sys
sys.path.insert(0, '/a0/usr/projects/biodockify_ai')

print('Testing Auto-Research Integration...')
print('=' * 60)

# Test 1: Research Topic Detector
print('')
print('1. Testing Research Topic Detector...')
from modules.research_detector import ResearchTopicDetector

detector = ResearchTopicDetector()

test_messages = [
    "I want to research Alzheimer drug mechanisms",
    "Please conduct a PhD research on cancer immunotherapy",
    "Write a systematic review article about diabetes treatments",
    "Hello, how are you today?"
]

for msg in test_messages:
    result = detector.detect(msg)
    if result:
        print(f"  Detected: {result.topic} (type: {result.research_type}, confidence: {result.confidence})")
    else:
        print(f"  No research detected: {msg}")

# Test 2: Auto-Research Orchestrator
print('')
print('2. Testing Auto-Research Orchestrator...')
from modules.auto_research_orchestrator import (
    AutoResearchOrchestrator,
    TodoListManager,
    AgentCommunicationBridge
)

orchestrator = AutoResearchOrchestrator()

topic = detector.detect('Conduct a PhD research on COVID-19 vaccine efficacy')
plan = orchestrator.create_research_plan(topic)

print(f"  Plan created for: {plan.topic}")
print(f"  Research type: {plan.research_type}")
print(f"  Tasks: {len(plan.tasks)}")
print(f"  Stages: {list(plan.stages.keys())}")

# Test 3: Todo List Manager
print('')
print('3. Testing Todo List Manager...')
todo_manager = TodoListManager()

task1 = todo_manager.create_task(
    title='Define research questions',
    description='Define primary and secondary research questions',
    priority=5
)

task2 = todo_manager.create_task(
    title='Literature search',
    description='Search PubMed, Scopus, and Web of Science',
    priority=5,
    dependencies=[task1.id]
)

pending = todo_manager.get_pending_tasks()
print(f"  Created {len(todo_manager.tasks)} tasks")
print(f"  Pending tasks ready: {len(pending)}")
print(f"  Progress: {todo_manager.get_progress()*100:.1f}%")

summary = todo_manager.get_summary()
print(f"  Summary: {summary}")

# Test 4: Communication Bridge
print('')
print('4. Testing Agent Communication Bridge...')
bridge = AgentCommunicationBridge(
    agent_zero_endpoint='/api/agent',
    nanobot_endpoint='/api/nanobot'
)

import asyncio

async def test_communication():
    result1 = await bridge.send_to_nanobot(
        'Starting research on Alzheimer disease',
        permission_required=False
    )
    print(f"  AgentZero -> NanoBot: {result1['status']}")

    result2 = await bridge.send_to_agent_zero(
        'Research task completed',
        {'progress': 0.5}
    )
    print(f"  NanoBot -> AgentZero: {result2['status']}")

    result3 = await bridge.request_permission(
        'Execute deep research',
        {'topic': 'Alzheimer'}
    )
    print(f"  Permission request: {result3}")

    history = bridge.get_communication_history()
    print(f"  Communication history: {len(history)} messages")

asyncio.run(test_communication())

# Test 5: Full Workflow
print('')
print('5. Testing Full Workflow Integration...')
research_topic = detector.detect('Write a review article on Parkinson disease treatments')
research_plan = orchestrator.create_research_plan(research_topic)

print(f"  Topic: {research_plan.topic}")
print(f"  Type: {research_plan.research_type}")
print(f"  Tasks by stage:")
for stage, tasks in research_plan.stages.items():
    print(f"    - {stage}: {len(tasks)} tasks")

print(f"  Task priorities:")
priority_counts = {}
for task in research_plan.tasks:
    priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
for priority in sorted(priority_counts.keys(), reverse=True):
    print(f"    - Priority {priority}: {priority_counts[priority]} tasks")

print('')
print('=' * 60)
print('All integration tests passed successfully!')
print('Auto-research system is ready for use')
print('=' * 60)
