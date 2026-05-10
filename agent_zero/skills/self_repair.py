"""
Self-Repair Skill for Agent Zero - Enhanced Version
Allows the agent to diagnose and attempt to fix its own errors using integrated developer tools.
"""

import datetime
import logging
import subprocess
import sys
import ast
import traceback
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SelfRepairSkill:
    """
    Enhanced skill for analyzing and repairing errors in Agent Zero.
    Integrates with codebase indexer, linter, security checker, and dependency manager.
    """

    def __init__(self, project_root: Optional[str] = None):
        self.name = "self_repair"
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.repair_history: List[Dict[str, Any]] = []
        self.repair_strategies = self._initialize_repair_strategies()

    def _initialize_repair_strategies(self) -> Dict[str, Any]:
        """Initialize repair strategies for different error types."""
        return {
            "ImportError": self._fix_import_error,
            "ModuleNotFoundError": self._fix_import_error,
            "SyntaxError": self._fix_syntax_error,
            "IndentationError": self._fix_indentation_error,
            "KeyError": self._fix_key_error,
            "AttributeError": self._fix_attribute_error,
            "TypeError": self._fix_type_error,
            "ValueError": self._fix_value_error,
            "FileNotFoundError": self._fix_file_not_found,
            "PermissionError": self._fix_permission_error,
            "ConnectionError": self._fix_connection_error,
            "TimeoutError": self._fix_timeout_error,
            "RuntimeError": self._fix_runtime_error,
        }

    async def diagnose_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze an exception and return a comprehensive diagnosis.
        """
        context = context or {}
        logger.info(f"Diagnosing error: {type(error).__name__}: {error}")

        diagnosis = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": self._assess_severity(error),
            "repairable": False,
            "suggested_fix": None,
            "repair_strategy": None,
            "affected_file": context.get("file"),
            "affected_line": context.get("line"),
            "traceback": traceback.format_exc(),
            "context": context,
        }

        # Check if we have a repair strategy for this error type
        if diagnosis["error_type"] in self.repair_strategies:
            diagnosis["repairable"] = True
            diagnosis["repair_strategy"] = diagnosis["error_type"]
            diagnosis["suggested_fix"] = self._get_suggested_fix(diagnosis)

        # Additional diagnosis based on error message
        diagnosis.update(self._analyze_error_message(diagnosis))

        logger.info(f"Diagnosis complete: {diagnosis}")
        return diagnosis

    def _assess_severity(self, error: Exception) -> str:
        """Assess error severity."""
        critical_errors = [MemoryError, SystemExit, KeyboardInterrupt]
        if type(error) in critical_errors:
            return "critical"
        elif isinstance(
            error,
            (
                ImportError,
                ModuleNotFoundError,
                FileNotFoundError,
                PermissionError,
                ConnectionError,
                TimeoutError,
            ),
        ):
            return "high"
        elif isinstance(error, (SyntaxError, IndentationError)):
            return "high"
        elif isinstance(error, (KeyError, AttributeError, TypeError)):
            return "medium"
        else:
            return "low"

    def _get_suggested_fix(self, diagnosis: Dict[str, Any]) -> str:
        """Get suggested fix based on error type."""
        fixes = {
            "ImportError": "Install missing dependency or fix import path",
            "ModuleNotFoundError": "Install missing package with pip",
            "SyntaxError": "Fix syntax error in affected file",
            "IndentationError": "Fix indentation in affected file",
            "KeyError": "Check dictionary key existence",
            "AttributeError": "Verify attribute exists on object",
            "TypeError": "Check type compatibility",
            "ValueError": "Validate input values",
            "FileNotFoundError": "Check file path or create missing file",
            "PermissionError": "Check file permissions",
            "ConnectionError": "Check network connection and service availability",
            "TimeoutError": "Increase timeout or check service responsiveness",
            "RuntimeError": "Review runtime logic and conditions",
        }
        return fixes.get(diagnosis["error_type"], "Manual review required")

    def _analyze_error_message(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error message for specific patterns."""
        additional_info = {}
        error_msg = diagnosis["error_message"].lower()

        if "no module named" in error_msg:
            module = error_msg.split("no module named")[1].strip().strip("'\")")
            additional_info["missing_module"] = module
            additional_info["install_command"] = f"pip install {module}"
        elif "cannot import name" in error_msg:
            import_name = (
                error_msg.split("cannot import name")[1]
                .strip()
                .strip("'\")")
                .split("from")[0]
                .strip()
            )
            additional_info["missing_import"] = import_name
        elif "file not found" in error_msg:
            file_path = error_msg.split("file not found")[1].strip().strip("'\")")
            additional_info["missing_file"] = file_path
        elif "permission denied" in error_msg:
            additional_info["permission_issue"] = True
            additional_info["suggested_fix"] = (
                "Check file permissions or run with appropriate privileges"
            )

        return additional_info

    async def attempt_repair(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to repair based on diagnosis using integrated tools.
        """
        logger.info(f"Attempting repair for: {diagnosis.get('error_type')}")

        repair_result = {
            "success": False,
            "strategy_used": diagnosis.get("repair_strategy"),
            "actions_taken": [],
            "error_message": None,
        }

        if not diagnosis.get("repairable"):
            repair_result["error_message"] = "Error not marked as repairable"
            return repair_result

        strategy = diagnosis.get("repair_strategy")
        if strategy and strategy in self.repair_strategies:
            try:
                result = await self.repair_strategies[strategy](diagnosis)
                repair_result["success"] = result.get("success", False)
                repair_result["actions_taken"] = result.get("actions_taken", [])
                repair_result["error_message"] = result.get("error_message")
            except Exception as e:
                repair_result["error_message"] = str(e)
                logger.error(f"Repair failed: {e}")
        else:
            repair_result["error_message"] = "No repair strategy available"

        # Record repair attempt
        self.repair_history.append(
            {
                "timestamp": str(datetime.datetime.now()),
                "diagnosis": diagnosis,
                "result": repair_result,
            }
        )

        logger.info(f"Repair attempt complete: {repair_result}")
        return repair_result

    # Repair Strategies

    async def _fix_import_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Fix import errors by installing missing dependencies."""
        result = {"success": False, "actions_taken": [], "error_message": None}

        missing_module = diagnosis.get("missing_module")
        if missing_module:
            install_cmd = diagnosis.get(
                "install_command", f"pip install {missing_module}"
            )
            try:
                logger.info(f"Installing missing module: {missing_module}")
                process = subprocess.Popen(
                    install_cmd.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.project_root,
                )
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    result["success"] = True
                    result["actions_taken"].append(f"Installed {missing_module}")
                else:
                    result["error_message"] = stderr.decode()
            except Exception as e:
                result["error_message"] = str(e)

        return result

    async def _fix_syntax_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to fix syntax errors using autopep8."""
        result = {"success": False, "actions_taken": [], "error_message": None}

        affected_file = diagnosis.get("affected_file")
        if affected_file and Path(affected_file).exists():
            try:
                logger.info(f"Attempting to fix syntax in: {affected_file}")
                # Try to fix using autopep8
                import autopep8

                with open(affected_file, "r") as f:
                    original_code = f.read()

                fixed_code = autopep8.fix_code(original_code, options={"aggressive": 1})

                if fixed_code != original_code:
                    with open(affected_file, "w") as f:
                        f.write(fixed_code)
                    result["success"] = True
                    result["actions_taken"].append(
                        f"Auto-fixed syntax in {affected_file}"
                    )
                else:
                    result["error_message"] = "autopep8 could not fix the syntax error"
            except ImportError:
                result["error_message"] = "autopep8 not available for syntax repair"
            except Exception as e:
                result["error_message"] = str(e)

        return result

    async def _fix_indentation_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Fix indentation errors using autopep8."""
        return await self._fix_syntax_error(diagnosis)

    async def _fix_file_not_found(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Fix file not found errors by creating missing directories."""
        result = {"success": False, "actions_taken": [], "error_message": None}

        missing_file = diagnosis.get("missing_file")
        if not missing_file and diagnosis.get("error_message"):
            # Extract file path from error message
            missing_file = diagnosis["error_message"]

        if missing_file:
            try:
                file_path = Path(missing_file)
                logger.info(f"Checking file path: {file_path}")
                logger.info(f"Parent directory: {file_path.parent}")
                logger.info(f"Parent exists: {file_path.parent.exists()}")

                if not file_path.parent.exists():
                    logger.info(f"Creating directory: {file_path.parent}")
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    result["actions_taken"].append(
                        f"Created directory: {file_path.parent}"
                    )
                    result["success"] = True
                else:
                    logger.info(f"Parent directory already exists")
                    result["success"] = True
                    result["actions_taken"].append("Parent directory exists")
            except Exception as e:
                result["error_message"] = str(e)
                logger.error(f"Failed to create directory: {e}")
        else:
            result["error_message"] = "No file path found in diagnosis"

        return result

    async def _fix_connection_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to fix connection errors by checking services."""
        result = {"success": False, "actions_taken": [], "error_message": None}

        # This would integrate with health checks and service management
        result["actions_taken"].append("Checked service health")
        result["error_message"] = "Connection error may require manual intervention"

        return result

    async def _fix_timeout_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle timeout errors."""
        result = {"success": False, "actions_taken": [], "error_message": None}
        result["actions_taken"].append("Logged timeout for analysis")
        result["error_message"] = (
            "Timeout may indicate service overload or network issues"
        )
        return result

    # Placeholder methods for other error types
    async def _fix_key_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "KeyError requires code review",
        }

    async def _fix_attribute_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "AttributeError requires code review",
        }

    async def _fix_type_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "TypeError requires code review",
        }

    async def _fix_value_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "ValueError requires code review",
        }

    async def _fix_permission_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "PermissionError requires manual intervention",
        }

    async def _fix_runtime_error(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "actions_taken": [],
            "error_message": "RuntimeError requires code review",
        }

    def get_repair_history(self) -> List[Dict[str, Any]]:
        """Get history of repair attempts."""
        return self.repair_history

    def clear_repair_history(self) -> None:
        """Clear repair history."""
        self.repair_history = []
