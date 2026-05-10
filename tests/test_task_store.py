import pytest
import asyncio
import tempfile
from pathlib import Path
from runtime.task_store import TaskStore


@pytest.mark.asyncio
async def test_task_creation(task_store):
    """Test creating a new task."""
    task = await task_store.create_task("task_1", "Test Task", "local")
    assert task["task_id"] == "task_1"
    assert task["status"] == "pending"
    assert task["title"] == "Test Task"
    
    # Verify persistence
    fetched = await task_store.get_task("task_1")
    assert fetched is not None
    assert fetched["task_id"] == "task_1"

@pytest.mark.asyncio
async def test_task_update(task_store):
    """Test updating task status and progress."""
    await task_store.create_task("task_2")
    
    success = await task_store.update_task("task_2", status="running", progress=50)
    assert success is True
    
    fetched = await task_store.get_task("task_2")
    assert fetched["status"] == "running"
    assert fetched["progress"] == 50

@pytest.mark.asyncio
async def test_append_log(task_store):
    """Test appending logs to a task."""
    await task_store.create_task("task_3")
    
    await task_store.append_log("task_3", "Log 1")
    await task_store.append_log("task_3", "Log 2")
    
    fetched = await task_store.get_task("task_3")
    assert len(fetched["logs"]) == 2
    assert fetched["logs"][0] == "Log 1"
    assert fetched["logs"][1] == "Log 2"

@pytest.mark.asyncio
async def test_list_tasks(task_store):
    """Test listing tasks."""
    await task_store.create_task("t1")
    await asyncio.sleep(0.1) # Ensure timestamp diff
    await task_store.create_task("t2")
    
    tasks = await task_store.list_tasks()
    assert len(tasks) == 2
    assert tasks[0]["task_id"] == "t2" # Most recent first
    assert tasks[1]["task_id"] == "t1"
