"""
Scientific Reproducibility Engine - BioDockify NanoBot
Handles dataset checksums, tool versioning, and experiment snapshots.
"""
import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import platform
import psutil

logger = logging.getLogger("nanobot.reproducibility")

class ReproducibilityEngine:
    """
    Scientific Reproducibility Snapshot Engine (SRSE).
    Captures Environment, Dataset, Parameters, Workflow, and Output layers.
    """
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.snapshots_dir = project_path / ".reproducibility" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        try:
            if not file_path.exists(): return "not_found"
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return f"error: {str(e)}"

    def get_dataset_fingerprint(self, dataset_path: Optional[str]) -> Dict[str, Any]:
        """Capture Layer 2: Dataset fingerprint."""
        if not dataset_path:
            return {"status": "none"}
        
        path = Path(dataset_path)
        if not path.exists():
            return {"status": "missing", "path": dataset_path}
            
        return {
            "status": "captured",
            "name": path.name,
            "path": str(path.absolute()),
            "size_bytes": path.stat().st_size,
            "sha256": self.calculate_checksum(path),
            "last_modified": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        }

    def get_environment_layer(self) -> Dict[str, Any]:
        """Capture Layer 1: Environment context."""
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "cpu_arch": platform.machine(),
            "tools": self.get_tool_versions(["vina", "gnina", "python", "gcc", "docker"])
        }

    def get_tool_versions(self, tool_names: List[str]) -> Dict[str, str]:
        """Capture tool versions with fallback to 'unknown'."""
        versions = {}
        for tool in tool_names:
            try:
                # Common version checks
                cmd = [tool, "--version"]
                if tool == "python": cmd = ["python", "-V"]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                versions[tool] = result.stdout.strip() or result.stderr.strip() or "unknown"
            except Exception:
                versions[tool] = "not_found"
        return versions

    def calculate_reproducibility_score(self, snapshot: Dict[str, Any]) -> int:
        """Calculate a percentage score based on data completeness."""
        score = 0
        checks = {
            "environment": bool(snapshot.get("environment")),
            "dataset": snapshot.get("dataset", {}).get("status") == "captured",
            "parameters": bool(snapshot.get("parameters")),
            "random_seed": "random_seed" in str(snapshot.get("parameters", "")).lower(),
            "workflow_state": bool(snapshot.get("workflow_state"))
        }
        
        weights = {"environment": 20, "dataset": 30, "parameters": 20, "random_seed": 20, "workflow_state": 10}
        for key, weight in weights.items():
            if checks.get(key):
                score += weight
        return score

    async def create_snapshot(self, 
                                label: str, 
                                dataset_path: Optional[str] = None,
                                parameters: Optional[Dict[str, Any]] = None,
                                workflow_state: Optional[Dict[str, Any]] = None,
                                outputs: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a multi-layered Scientific Reproducibility Snapshot.
        """
        snapshot_id = f"snap_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.json"
        
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            
            "environment": self.get_environment_layer(),           # Layer 1
            "dataset": self.get_dataset_fingerprint(dataset_path), # Layer 2
            "parameters": parameters or {},                       # Layer 3
            "workflow_state": workflow_state or {},               # Layer 4
            "outputs": outputs or {},                             # Layer 5
            
            "reproducibility_score": 0
        }
        
        snapshot_data["reproducibility_score"] = self.calculate_reproducibility_score(snapshot_data)
        
        try:
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
            
            # Log to audit trail (if integrated, handled by receptionist typically)
            logger.info(f"SRSE Snapshot {snapshot_id} created. Score: {snapshot_data['reproducibility_score']}%")
            return snapshot_id
        except Exception as e:
            logger.error(f"Failed to create SRSE snapshot: {e}")
            return f"error: {str(e)}"

    def verify_reproducibility(self, snapshot_id: str, current_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current state against a historical snapshot."""
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.json"
        if not snapshot_path.exists():
            return {"status": "error", "message": "Snapshot not found"}
            
        with open(snapshot_path, "r") as f:
            historical = json.load(f)
            
        diffs = []
        # Check tool versions
        current_tools = self.get_tool_versions(list(historical["tool_versions"].keys()))
        for tool, version in historical["tool_versions"].items():
            if current_tools.get(tool) != version:
                diffs.append(f"Tool mismatch: {tool} ({version} vs {current_tools.get(tool)})")
                
        return {
            "status": "reproducible" if not diffs else "drift_detected",
            "diffs": diffs,
            "snapshot_timestamp": historical["timestamp"]
        }
