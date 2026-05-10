import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from modules.enhanced_integration.enhanced_system import get_enhanced_system
from modules.project_planner.project_planner import ProjectType
from modules.multi_task.multi_task_scheduler import TaskStatus


async def test_integrated_flow():
    print("Starting Integrated Flow Test...")

    # Initialize system
    system = get_enhanced_system(max_parallel_tasks=3)
    await system.initialize("integrated_test_device")
    await system.start()

    print("System initialized and started.")

    # 1. Create a project
    project_title = "Integrated Research Project"
    result = await system.create_project(
        project_title=project_title,
        project_type=ProjectType.RESEARCH,
        additional_context="Testing full integration",
    )

    project_id = result["project_id"]
    print(f"Created project: {project_title} (ID: {project_id})")

    # 2. Check initial status
    status = await system.get_project_status(project_id)
    print(f"Initial progress: {status['progress']['progress']}%")
    assert status["progress"]["progress"] == 0

    # 3. Simulate progress update
    first_task_id = status["tasks"][0]["id"]
    print(f"Updating progress for task {first_task_id}...")
    await system.update_task_progress(project_id, first_task_id, 50.0)

    status = await system.get_project_status(project_id)
    print(f"Progress after 50% update: {status['progress']['progress']}%")

    # 4. Simulate task completion
    print(f"Completing task {first_task_id}...")
    await system.update_task_progress(project_id, first_task_id, 100.0)

    status = await system.get_project_status(project_id)
    print(f"Progress after completion: {status['progress']['progress']}%")
    assert status["progress"]["completed_tasks"] == 1

    # 5. Test suspension and restoration
    print("Suspending system...")
    await system.suspend_and_save()

    print("Resuming system...")
    await system.resume_and_restore()

    # Verify that we can still get status
    status = await system.get_project_status(project_id)
    print(f"Status after resume: {status['project']['status']}")
    assert status["project"]["id"] == project_id

    # 6. Verify persistence
    print("Checking scheduler persistence...")
    # Scheduler should have saved its state
    persistence_file = Path("./data/scheduler_state.json")
    assert persistence_file.exists()

    await system.stop()
    print("\nINTEGRATED FLOW TEST PASSED!")


async def main():
    # Setup logging to be less verbose for the test
    logging.basicConfig(level=logging.ERROR)

    import tempfile
    import shutil

    # Create a temporary directory for the test databases
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Running tests in temporary directory: {temp_dir}")

        # Patch the paths/environment to use this temp dir
        # We need to ensure that the modules use this path for their DBs
        # Since we can't easily patch global variables in already imported modules,
        # we might need to rely on the modules respecting an env var or
        # creating the system with specific paths if supported.

        # Taking a simpler approach: Monkey-patch the defaults/constants if possible
        # Or better, check if we can pass valid paths to the factory functions.

        # Looking at get_enhanced_system, it doesn't seem to take DB paths directly.
        # However, TaskRepository takes db_url.

        # Let's try setting an env var that config_loader might pick up,
        # or monkey-patching the repository creation if possible.

        # Set enviroment variable for TaskStore and other components
        os.environ["BIODOCKIFY_DATA_DIR"] = temp_dir

        original_cwd = os.getcwd()
        try:
            # Change CWD to temp dir so relative paths work (if any remain)
            os.chdir(temp_dir)
            # Create necessary subdirectories
            os.makedirs("data", exist_ok=True)

            await test_integrated_flow()
        except Exception as e:
            print(f"\nTEST FAILED: {e}")
            import traceback

            traceback.print_exc()
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    asyncio.run(main())
