"""
Enhanced Project API Endpoints
REST API for project-based task management with device awareness
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any

from modules.enhanced_integration.enhanced_system import get_enhanced_system
from modules.project_planner.project_planner import ProjectType

router = APIRouter(prefix="/api/enhanced", tags=["Enhanced Project"])


@router.post("/project")
async def create_project(
    project_title: str,
    project_type: str = "research",
    additional_context: Optional[str] = None
):
    """
    Create a new project with comprehensive task list
    
    Args:
        project_title: Title of the project
        project_type: Type of project (research, development, writing, review, grant_application, publication, clinical_trial, thesis, lab_experiment)
        additional_context: Any additional details
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        # Parse project type
        try:
            ptype = ProjectType(project_type.lower())
        except ValueError:
            ptype = ProjectType.RESEARCH

        result = await enhanced_system.create_project(
            project_title=project_title,
            project_type=ptype,
            additional_context=additional_context
        )

        return {
            "status": "success",
            "project": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/project/{project_id}")
async def get_project_status(project_id: str):
    """
    Get comprehensive project status including:
    - Project details
    - Progress
    - Task list
    - Device status
    - Task queue status
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        status = await enhanced_system.get_project_status(project_id)
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project status: {str(e)}")


@router.post("/project/{project_id}/task/{task_id}/progress")
async def update_task_progress(
    project_id: str,
    task_id: str,
    progress: float
):
    """
    Update progress for a task in a project
    
    Args:
        project_id: Project ID
        task_id: Task ID
        progress: Progress percentage (0-100)
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        result = await enhanced_system.update_task_progress(
            project_id=project_id,
            task_id=task_id,
            progress=progress
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task progress: {str(e)}")


@router.post("/project/{project_id}/task/{task_id}/complete")
async def complete_task(
    project_id: str,
    task_id: str,
    result_data: Optional[Dict[str, Any]] = None
):
    """
    Mark a task as completed with results
    
    Args:
        project_id: Project ID
        task_id: Task ID
        result_data: Results from task execution
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        await enhanced_system.complete_task(
            project_id=project_id,
            task_id=task_id,
            result_data=result_data or {}
        )

        return {
            "status": "success",
            "message": f"Task {task_id} marked as completed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete task: {str(e)}")


@router.post("/device/suspend")
async def suspend_device():
    """
    Suspend all work and save state
    Called when device goes offline
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        await enhanced_system.suspend_and_save()

        return {
            "status": "success",
            "message": "Device suspended, state saved"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suspend device: {str(e)}")


@router.post("/device/resume")
async def resume_device():
    """
    Resume work and restore state
    Called when device comes online
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        await enhanced_system.resume_and_restore()

        return {
            "status": "success",
            "message": "Device resumed, state restored"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume device: {str(e)}")


@router.get("/system/status")
async def get_system_status():
    """
    Get comprehensive system status
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        status = await enhanced_system.get_system_status()
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


@router.get("/projects")
async def list_projects(
    project_type: Optional[str] = None
):
    """
    List all projects, optionally filtered by type
    """
    try:
        enhanced_system = get_enhanced_system()
        if not enhanced_system:
            raise HTTPException(status_code=503, detail="System not initialized")

        system_status = await enhanced_system.get_system_status()
        projects = system_status.get("projects", [])

        if project_type:
            projects = [p for p in projects if p.get("project_type") == project_type]

        return {
            "status": "success",
            "projects": projects
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")
