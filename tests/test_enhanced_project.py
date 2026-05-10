
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from modules.project_planner.project_planner import ProjectPlanner, ProjectType, ProjectPhase
from modules.device_manager.device_state_manager import DeviceStateManager, DeviceState
from modules.multi_task.multi_task_scheduler import MultiTaskScheduler, TaskStatus

async def test_planner():
    print("Testing Project Planner...")
    planner = ProjectPlanner()
    project = await planner.create_project_from_title(
        "AI Drug Discovery - Phase 1",
        project_type=ProjectType.RESEARCH,
        additional_context="Focus on small molecules"
    )
    
    print(f"Project Created: {project.title}")
    print(f"Total Tasks: {len(project.tasks)}")
    
    # Verify templates
    assert len(project.tasks) >= 5
    assert project.tasks[0].phase == ProjectPhase.PLANNING
    
    print("Project Planner Test Passed")

async def test_device_manager():
    print("Testing Device State Manager...")
    manager = DeviceStateManager()
    await manager.initialize("test_device_001")
    
    assert manager.current_device_id == "test_device_001"
    
    session = await manager.create_session("proj_123")
    assert session.device_id == "test_device_001"
    assert "proj_123" in manager.active_projects
    
    await manager.suspend()
    assert manager.current_session.state == DeviceState.SUSPENDED
    
    print("Device State Manager Test Passed")

async def test_scheduler():
    print("Testing Multi-Task Scheduler...")
    scheduler = MultiTaskScheduler(max_parallel_tasks=2)
    
    # Mocking task manager integration for simple test
    await scheduler.add_task("t1", "Task 1", "Desc 1", priority=0)
    await scheduler.add_task("t2", "Task 2", "Desc 2", priority=1)
    await scheduler.add_task("t3", "Task 3", "Desc 3", priority=2, dependencies=["t1"])
    
    await scheduler.start_next_tasks()
    
    # t1 and t2 should start, t3 should wait
    assert "t1" in scheduler.running_tasks
    assert "t2" in scheduler.running_tasks
    assert "t3" not in scheduler.running_tasks
    
    print("Multi-Task Scheduler Test Passed")

async def main():
    try:
        await test_planner()
        await test_device_manager()
        await test_scheduler()
        print("\nALL ENHANCED PROJECT SYSTEM TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
