"""
Agent Zero - Persistent Memory System
Stores learned patterns, successful solutions, and facts across sessions.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger("memory_store")


class MemoryType(Enum):
    """Types of memories the agent can store."""
    EPISODIC = "episodic"      # Past actions and their outcomes
    SEMANTIC = "semantic"      # Facts and knowledge
    PROCEDURAL = "procedural"  # How-to procedures and solutions


class MemoryStore:
    """
    Persistent memory storage for Agent Zero.
    Uses SQLite for durability and fast retrieval.
    """
    
    MAX_MEMORIES = 10000  # Maximum memories to store
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to user's home directory
            home = Path.home()
            data_dir = home / ".biodockify" / "agent_memory"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "memories.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    tags TEXT,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    metadata TEXT
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC)
            ''')
            conn.commit()
    
    def store(
        self,
        content: str,
        memory_type: MemoryType,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a new memory.
        
        Args:
            content: The memory content
            memory_type: Type of memory (episodic, semantic, procedural)
            tags: Optional tags for categorization
            importance: Importance score (0.0 - 1.0)
            metadata: Additional metadata
        
        Returns:
            Memory ID
        """
        # Check memory limit and prune if needed
        self._prune_if_needed()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memories (content, memory_type, tags, importance, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                content,
                memory_type.value,
                json.dumps(tags or []),
                min(max(importance, 0.0), 1.0),  # Clamp to [0, 1]
                json.dumps(metadata or {})
            ))
            conn.commit()
            memory_id = cursor.lastrowid
        
        logger.info(f"Stored memory #{memory_id} (type={memory_type.value})")
        return memory_id
    
    def recall(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recall memories matching the query.
        Uses simple text matching (for full semantic search, integrate with vector store).
        
        Args:
            query: Search query
            memory_type: Optional filter by memory type
            limit: Maximum memories to return
        
        Returns:
            List of matching memories
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build query
            sql = '''
                SELECT id, content, memory_type, tags, importance, access_count, 
                       created_at, last_accessed, metadata
                FROM memories
                WHERE content LIKE ?
            '''
            params = [f"%{query}%"]
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.value)
            
            sql += " ORDER BY importance DESC, access_count DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Update access counts
            for row in rows:
                cursor.execute('''
                    UPDATE memories 
                    SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (row[0],))
            conn.commit()
        
        return [
            {
                "id": row[0],
                "content": row[1],
                "memory_type": row[2],
                "tags": json.loads(row[3]) if row[3] else [],
                "importance": row[4],
                "access_count": row[5],
                "created_at": row[6],
                "last_accessed": row[7],
                "metadata": json.loads(row[8]) if row[8] else {}
            }
            for row in rows
        ]
    
    def recall_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recall the most recent memories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, memory_type, importance, created_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "content": row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                "memory_type": row[2],
                "importance": row[3],
                "created_at": row[4]
            }
            for row in rows
        ]
    
    def recall_important(self, threshold: float = 0.7, limit: int = 10) -> List[Dict[str, Any]]:
        """Recall high-importance memories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, memory_type, importance, access_count
                FROM memories
                WHERE importance >= ?
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
            ''', (threshold, limit))
            rows = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "content": row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                "memory_type": row[2],
                "importance": row[3],
                "access_count": row[4]
            }
            for row in rows
        ]
    
    def update_importance(self, memory_id: int, importance: float):
        """Update the importance of a memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memories SET importance = ? WHERE id = ?
            ''', (min(max(importance, 0.0), 1.0), memory_id))
            conn.commit()
    
    def delete(self, memory_id: int):
        """Delete a specific memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            conn.commit()
    
    def _prune_if_needed(self):
        """Remove old, low-importance memories if limit exceeded."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM memories')
            count = cursor.fetchone()[0]
            
            if count >= self.MAX_MEMORIES:
                # Delete oldest, least important memories
                delete_count = count - self.MAX_MEMORIES + 100  # Delete extra buffer
                cursor.execute('''
                    DELETE FROM memories WHERE id IN (
                        SELECT id FROM memories
                        ORDER BY importance ASC, access_count ASC, created_at ASC
                        LIMIT ?
                    )
                ''', (delete_count,))
                conn.commit()
                logger.info(f"Pruned {delete_count} old memories")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM memories')
            total = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type
            ''')
            by_type = dict(cursor.fetchall())
            
            cursor.execute('SELECT AVG(importance) FROM memories')
            avg_importance = cursor.fetchone()[0] or 0
        
        return {
            "total_memories": total,
            "by_type": by_type,
            "average_importance": round(avg_importance, 2),
            "max_capacity": self.MAX_MEMORIES
        }
    
    def clear_all(self):
        """Clear all memories (use with caution)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memories')
            conn.commit()
        logger.warning("All memories cleared!")


# Global memory store instance
memory_store = MemoryStore()


# API-friendly helper functions
def remember(content: str, memory_type: str = "semantic", importance: float = 0.5) -> Dict[str, Any]:
    """Store a memory (API-friendly)."""
    try:
        mtype = MemoryType(memory_type)
    except ValueError:
        mtype = MemoryType.SEMANTIC
    
    memory_id = memory_store.store(content, mtype, importance=importance)
    return {
        "status": "success",
        "memory_id": memory_id,
        "message": f"Memory stored successfully (type={memory_type})."
    }


def recall(query: str, memory_type: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Recall memories (API-friendly)."""
    mtype = None
    if memory_type:
        try:
            mtype = MemoryType(memory_type)
        except ValueError:
            pass
    
    memories = memory_store.recall(query, mtype, limit)
    return {
        "status": "success",
        "count": len(memories),
        "memories": memories
    }
