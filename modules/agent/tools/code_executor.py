"""
Agent Zero - Sandboxed Code Executor
Allows safe execution of Python code with timeouts and module restrictions.
"""

import sys
import io
import traceback
import multiprocessing
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("code_executor")

# Whitelisted modules for safe execution
SAFE_MODULES = {
    'math', 'statistics', 'random', 'datetime', 'time',
    'json', 're', 'collections', 'itertools', 'functools',
    'numpy', 'pandas', 'scipy',  # Scientific computing
    'string', 'textwrap', 'difflib',
}

# Blacklisted functions/attributes
BLACKLIST = {
    'exec', 'eval', 'compile', '__import__', 'open', 'file',
    'input', 'raw_input', 'exit', 'quit', 'help',
    'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr', 'delattr',
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests',
}


def _execute_code_worker(code: str, result_queue: multiprocessing.Queue):
    """Worker function that runs in a separate process for isolation."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    result = {
        "success": False,
        "output": "",
        "error": "",
        "return_value": None
    }
    
    try:
        # Redirect stdout/stderr
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_capture, stderr_capture
        
        # Create restricted globals
        safe_globals = {"__builtins__": {}}
        
        # Add safe builtins
        safe_builtins = [
            'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'chr', 'dict',
            'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
            'hash', 'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len',
            'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow', 'print',
            'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
            'str', 'sum', 'tuple', 'type', 'zip'
        ]
        
        import builtins
        for name in safe_builtins:
            if hasattr(builtins, name):
                safe_globals["__builtins__"][name] = getattr(builtins, name)
        
        # Import safe modules
        for module_name in SAFE_MODULES:
            try:
                module = __import__(module_name)
                safe_globals[module_name] = module
            except ImportError:
                pass  # Module not available
        
        # Add common aliases
        if 'numpy' in safe_globals:
            safe_globals['np'] = safe_globals['numpy']
        if 'pandas' in safe_globals:
            safe_globals['pd'] = safe_globals['pandas']
        
        # Execute the code
        exec(code, safe_globals)
        
        result["success"] = True
        result["output"] = stdout_capture.getvalue()
        
    except Exception as e:
        result["success"] = False
        result["error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        result["output"] = stdout_capture.getvalue()
        
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    
    result_queue.put(result)


def execute_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed environment.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 30)
    
    Returns:
        Dict with keys: success, output, error, return_value
    """
    # Security check - reject obvious dangerous patterns
    code_lower = code.lower()
    for blocked in BLACKLIST:
        if blocked in code_lower:
            return {
                "success": False,
                "output": "",
                "error": f"Security: '{blocked}' is not allowed in code execution.",
                "return_value": None
            }
    
    # Check for import of non-whitelisted modules
    import re
    import_pattern = r'import\s+(\w+)|from\s+(\w+)'
    imports = re.findall(import_pattern, code)
    for match in imports:
        module = match[0] or match[1]
        if module and module not in SAFE_MODULES:
            return {
                "success": False,
                "output": "",
                "error": f"Security: Module '{module}' is not whitelisted. Allowed: {', '.join(sorted(SAFE_MODULES))}",
                "return_value": None
            }
    
    # Execute in a separate process with timeout
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_execute_code_worker,
        args=(code, result_queue)
    )
    
    try:
        process.start()
        process.join(timeout=timeout)
        
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {timeout} seconds.",
                "return_value": None
            }
        
        if not result_queue.empty():
            return result_queue.get()
        else:
            return {
                "success": False,
                "output": "",
                "error": "No result returned from execution.",
                "return_value": None
            }
            
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "return_value": None
        }


# Singleton executor instance
class CodeExecutor:
    """Wrapper class for code execution with logging and metrics."""
    
    def __init__(self):
        self.execution_count = 0
        self.success_count = 0
    
    def run(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute code and track metrics."""
        self.execution_count += 1
        result = execute_code(code, timeout)
        if result["success"]:
            self.success_count += 1
        
        logger.info(f"Code execution #{self.execution_count}: success={result['success']}")
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """Get execution statistics."""
        return {
            "total": self.execution_count,
            "success": self.success_count,
            "failed": self.execution_count - self.success_count
        }


# Global executor instance
executor = CodeExecutor()
