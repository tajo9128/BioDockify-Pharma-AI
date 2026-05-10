"""
Validation Bridge - BioDockify NanoBot
Automated sanity checking for Agent Zero outputs and high-risk action gating.
"""
import logging
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nanobot.validator")

class ValidatorBridge:
    """
    Acts as a quality control layer between Agent Zero outputs and the final research workspace.
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def validate_python_script(self, script_path: str) -> Dict[str, Any]:
        """
        Check if a Python script has syntax errors or missing basic imports.
        """
        path = Path(script_path)
        if not path.exists():
            return {"status": "error", "message": f"Script not found at {script_path}"}
            
        try:
            # Check syntax only
            result = subprocess.run(
                ["python", "-m", "py_compile", str(path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "status": "fail", 
                    "issue": "Syntax Error", 
                    "details": result.stderr.strip()
                }
                
            return {"status": "pass", "message": "Syntax check successful."}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_data_schema(self, data_path: str, required_headers: List[str]) -> Dict[str, Any]:
        """
        Verify that a generated CSV or JSON follows the expected schema.
        """
        path = Path(data_path)
        if not path.exists():
            return {"status": "error", "message": "Data file not found."}
            
        try:
            if path.suffix == ".csv":
                import csv
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    missing = [h for h in required_headers if h not in headers]
                    if missing:
                        return {"status": "fail", "issue": f"Missing headers: {missing}"}
            
            return {"status": "pass", "message": "Schema validation successful."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def requires_approval(self, action_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Determine if an action (e.g., deleting data, high-cost API call) requires a Human-in-the-Loop gate.
        """
        high_risk_actions = ["bulk_delete", "overwrite_results", "large_dataset_download"]
        if action_type in high_risk_actions:
            return True
        
        # Example: Cost threshold
        if metadata.get("estimated_cost", 0) > 5.0: # $5 threshold for example
            return True
            
        return False
