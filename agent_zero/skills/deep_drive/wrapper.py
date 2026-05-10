"""
Deep Drive Forensics Integration Wrapper
Wraps PAN code functionality for Agent Zero.
"""
import os
import sys
from typing import Optional, List, Dict, Any
from loguru import logger
from pathlib import Path
import threading

class DeepDriveSkill:
    """
    Skill wrapper for Deep Drive (PAN Code) forensic analysis.
    """
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.pan_code_path = self.base_path
        
        # Ensure pan-code path is in sys.path for internal script calls if needed
        if str(self.pan_code_path) not in sys.path:
            sys.path.append(str(self.pan_code_path))

    def list_clef_tasks(self) -> List[str]:
        """List available CLEF tasks within the repository."""
        tasks = [d.name for d in self.pan_code_path.iterdir() if d.is_dir() and d.name.startswith(('clef', 'fire', 'semeval'))]
        return sorted(tasks)

    def analyze_authorship(self, text: str, task_year: str = "clef24") -> Dict[str, Any]:
        """
        Stub for authorship analysis. 
        In a real implementation, this would call specialized scripts 
        within the clefXX directories.
        """
        logger.info(f"Analyzing authorship using {task_year} logic...")
        # For now, return a structured placeholder that Agent Zero can reason about
        return {
            "task": task_year,
            "analysis_type": "Authorship Attribution",
            "status": "Ready for specific model execution",
            "capability": "Forensic style analysis"
        }

    def get_task_readme(self, task_name: str) -> str:
        """Fetch documentation for a specific PAN task."""
        readme_path = self.pan_code_path / task_name / "README.md"
        if readme_path.exists():
            return readme_path.read_text(encoding='utf-8')
        return f"No README found for task {task_name}"

# Singleton
_deep_drive_instance = None
_deep_drive_lock = threading.Lock()

def get_deep_drive() -> DeepDriveSkill:
    global _deep_drive_instance
    with _deep_drive_lock:
        if not _deep_drive_instance:
            _deep_drive_instance = DeepDriveSkill()
    return _deep_drive_instance
