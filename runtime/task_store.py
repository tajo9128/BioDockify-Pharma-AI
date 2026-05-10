"""
Persistent Task Storage
Provides SQLite-backed task storage for research tasks.
"""

"""
Persistent Task Storage
Provides SQLite-backed task storage for research tasks.
"""

import aiosqlite
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("task_store")

class TaskStore:
    """
    Persistent task storage using aiosqlite.
    Async-native for non-blocking I/O.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Check env var first
            import os
            env_path = os.getenv("BIODOCKIFY_DATA_DIR")
            if env_path:
                db_path = Path(env_path) / "tasks.db"
            else:
                db_path = Path.home() / ".biodockify" / "data" / "tasks.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # We don't init DB in __init__ because it's sync. 
        # Application startup should call await store.init()
    
    async def init(self):
        """Initialize the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    title TEXT,
                    mode TEXT,
                    logs TEXT DEFAULT '[]',
                    result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()
        logger.info(f"TaskStore initialized at {self.db_path}")
    
    async def create_task(self, task_id: str, title: str = "", mode: str = "local") -> Dict[str, Any]:
        """Create a new task."""
        now = datetime.now().isoformat()
        task = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "title": title,
            "mode": mode,
            "logs": [],
            "result": None,
            "created_at": now,
            "updated_at": now
        }
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO tasks (task_id, status, progress, title, mode, logs, result, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, "pending", 0, title, mode, 
                    json.dumps([]), None, now, now
                ))
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to create task: {e}")
                raise
        
        return task
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
        return None
    
    async def update_task(self, task_id: str, **updates) -> bool:
        """Update a task's fields."""
        if not updates:
            return False
        
        # 1. Validate Columns (Whitelist to prevent SQL Injection)
        VALID_COLUMNS = {
            "current_task", "current_step", "total_steps", 
            "progress_percent", "is_running", "latest_thinking", 
            "recent_log", "logs", "result", "updated_at", "status", "progress"
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in VALID_COLUMNS}
        
        if not filtered_updates:
            return False

        # Handle logs specially
        if "logs" in filtered_updates and isinstance(filtered_updates["logs"], list):
            filtered_updates["logs"] = json.dumps(filtered_updates["logs"])
        
        if "result" in filtered_updates and isinstance(filtered_updates["result"], dict):
            filtered_updates["result"] = json.dumps(filtered_updates["result"])
        
        filtered_updates["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in filtered_updates.keys()])
        values = list(filtered_updates.values()) + [task_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values)  # nosec B608
                await db.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to update task: {e}")
                return False
    
    async def append_log(self, task_id: str, log: str) -> bool:
        """Append a log entry to a task efficiently."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get existing logs
            async with db.execute("SELECT logs FROM tasks WHERE task_id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                
                try:
                    logs = json.loads(row["logs"]) if row["logs"] else []
                except:
                    logs = []
                
                logs.append(log)
                
                cursor = await db.execute(
                    "UPDATE tasks SET logs = ?, updated_at = ? WHERE task_id = ?",
                    (json.dumps(logs), datetime.now().isoformat(), task_id)
                )
                await db.commit()
                return cursor.rowcount > 0

    async def list_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all tasks, most recent first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Delete tasks older than specified days."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE created_at < ?", (cutoff,))
            await db.commit()
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old tasks")
            return deleted
    
    def _row_to_dict(self, row: aiosqlite.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        d = dict(row)
        
        # Parse JSON fields
        if d.get("logs"):
            try:
                d["logs"] = json.loads(d["logs"])
            except:
                d["logs"] = []
        else:
            d["logs"] = []
        
        if d.get("result"):
            try:
                d["result"] = json.loads(d["result"])
            except:
                pass
        
        return d


# Global singleton
_task_store: Optional[TaskStore] = None


def get_task_store() -> TaskStore:
    """Get the global TaskStore singleton."""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store
