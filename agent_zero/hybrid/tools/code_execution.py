"""
Code Execution Tool - Safe shell command execution.
Allows the agent to run diagnosis commands and python scripts.
"""
import asyncio
import logging
import subprocess
from typing import Tuple

logger = logging.getLogger(__name__)

class SafeCodeExecutionTool:
    """
    Executes code/commands in the safer environment (Docker).
    """
    
    def __init__(self, allowed_commands: list = None):
        self.allowed_commands = allowed_commands or [
            "ls", "cat", "head", "tail", "grep", "find", "mkdir", "cp", "mv", 
            "python", "pip", "npm", "bun", "curl", "wmic", "df", "free"
        ]
        
    async def execute_shell(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Run a shell command safely.
        """
        logger.info(f"Executing: {command}")
        
        # 1. Basic sanitization
        command = command.strip()
        if not command:
            return -1, "", "Error: Empty command"

        # 2. Block dangerous shell patterns even in arguments
        blocked_patterns = [";", "&&", "||", "|", ">", "<", "`", "$(", "\\"]
        for pattern in blocked_patterns:
            if pattern in command:
                 return -1, "", f"Error: Dangerous character '{pattern}' detected in command."

        # 3. Whitelist check on base command
        parts = command.split()
        cmd_base = parts[0]
        if self.allowed_commands and cmd_base not in self.allowed_commands:
             return -1, "", f"Error: Command '{cmd_base}' is not in the allowed whitelist."

        try:
            # 4. Use create_subprocess_exec (list-based) to prevent shell injection
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                rc = proc.returncode
                
                out_str = stdout.decode().strip()
                err_str = stderr.decode().strip()
                
                return rc, out_str, err_str
                
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except:
                    pass
                return -1, "", "Command timed out"
                
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return -1, "", str(e)

    async def execute_python(self, code: str) -> str:
        """Execute a snippet of Python code with robust cleanup."""
        import tempfile
        import os
        
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                tmp_path = f.name
                
            rc, out, err = await self.execute_shell(f"python {tmp_path}")
            
            if rc != 0:
                return f"Error ({rc}):\n{err}"
            return out
            
        except Exception as e:
            return f"Python execution logic failed: {e}"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {tmp_path}: {e}")
