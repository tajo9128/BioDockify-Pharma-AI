"""
File Editor Tool - Allows the agent to read and modify files.
ESSENTIAL for self-repair and code editing.
"""
import os
import logging
import shutil
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

class FileEditorTool:
    """
    Safe file operations for the agent.
    """
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        
    def _is_safe_path(self, path: str) -> bool:
        """Prevent escaping the root directory (path traversal)."""
        try:
            abs_path = os.path.abspath(path)
            # Use relpath to check if it points outside root
            rel = os.path.relpath(abs_path, self.root_dir)
            safe = not rel.startswith('..') and not os.path.isabs(rel)
            
            if not safe:
                # Check for bypass flag
                if os.getenv("BIO_FULL_ACCESS", "false").lower() == "true":
                    logger.warning(f"FileEditor: Allowing access outside root due to BIO_FULL_ACCESS: {path}")
                    return True
                return False
            return True
        except Exception:
            return False

    def read_file(self, params: dict) -> str:
        """
        Read content of a file.
        params: {"path": "relative/path/to/file"}
        """
        path = params.get("path") or params.get("file")
        if not path: return "Error: 'path' parameter is required"
        
        try:
            if not self._is_safe_path(path):
                return f"Error: Path '{path}' outside allowed directory."
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    def write_file(self, params: dict) -> str:
        """
        Write content to a file (OVERWRITE) with backup and atomic safety.
        params: {"path": "...", "content": "..."}
        """
        path = params.get("path") or params.get("file")
        content = params.get("content")
        
        if not path or content is None: return "Error: 'path' and 'content' are required"
        if not self._is_safe_path(path): return f"Error: Path '{path}' outside allowed directory."
        
        backup_created = False
        backup_path = f"{path}.bak"
        
        try:
            # 1. Create directory
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # 2. Create backup if file exists
            if os.path.exists(path):
                shutil.copy2(path, backup_path)
                backup_created = True
            
            # 3. Atomic Write via Temp File
            fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                os.replace(tmp_path, path)
            except Exception:
                if os.path.exists(tmp_path): os.remove(tmp_path)
                raise
            
            msg = f"Successfully wrote to {path}"
            if backup_created: msg += f" (Backup created at {backup_path})"
            return msg
            
        except Exception as e:
            # Restore backup if failure occurred
            if backup_created and os.path.exists(backup_path):
                shutil.copy2(backup_path, path)
            return f"Error writing file {path}: {str(e)}"

    def replace_in_file(self, params: dict) -> str:
        """
        Replace string in file.
        params: {"path": "...", "old": "...", "new": "...", "first_only": bool}
        """
        path = params.get("path") or params.get("file")
        old_str = params.get("old")
        new_str = params.get("new")
        first_only = params.get("first_only", False)
        
        if not path or old_str is None or new_str is None: 
            return "Error: 'path', 'old', and 'new' are required"
        if not self._is_safe_path(path): return f"Error: Path '{path}' outside allowed directory."
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_str not in content:
                return f"Error: '{old_str}' not found in {path}"
                
            if first_only:
                new_content = content.replace(old_str, new_str, 1)
            else:
                new_content = content.replace(old_str, new_str)
            
            # Re-use write_file for atomic safety and backup
            return self.write_file({"path": path, "content": new_content})
            
        except Exception as e:
            return f"Error replacing in file {path}: {str(e)}"
