"""
Persistent memory across PhD years

This module provides:
- Long-term persistent storage for research activities
- Short-term memory for current sessions
- Semantic search and retrieval
- Context generation for different PhD stages
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    task: Dict
    result: Dict
    phd_stage: str
    goal: str
    timestamp: str
    embedding: Optional[List[float]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryEntry':
        """Create from dictionary"""
        return cls(
            task=data.get('task', {}),
            result=data.get('result', {}),
            phd_stage=data.get('phd_stage', 'unknown'),
            goal=data.get('goal', ''),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            embedding=data.get('embedding'),
            tags=data.get('tags'),
            metadata=data.get('metadata')
        )


class PersistentMemory:
    """
    Persistent memory storage for Agent Zero

    Features:
    - Short-term memory for current session
    - Long-term persistent storage on disk
    - Keyword-based search
    - Context generation by PhD stage
    - Memory pruning for efficiency
    - Export and import capabilities

    Attributes:
        path: Storage path for memory files
        short_term: List of memories from current session
        long_term: List of all memories loaded from disk
    """

    def __init__(
        self,
        storage_path: str = './data/agent_memory',
        max_long_term: int = 10000,
        max_short_term: int = 100
    ):
        """
        Initialize persistent memory

        Args:
            storage_path: Directory path for storing memory files
            max_long_term: Maximum number of long-term memories to keep
            max_short_term: Maximum number of short-term memories to keep
        """
        self.path = Path(storage_path)
        self.path.mkdir(parents=True, exist_ok=True)

        self.max_long_term = max_long_term
        self.max_short_term = max_short_term

        self.short_term: List[Dict] = []
        self.long_term: List[Dict] = []

        self._load_long_term()
        logger.info(f"Initialized persistent memory at {self.path}")
        logger.info(f"Loaded {len(self.long_term)} memories from disk")

    async def store(
        self,
        memory: Dict,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store memory for long-term retention

        Args:
            memory: Dictionary containing task, result, goal, etc.
            tags: Optional list of tags for categorization
            metadata: Optional additional metadata

        Returns:
            Timestamp of stored memory
        """
        # Add timestamp if not present
        if 'timestamp' not in memory:
            memory['timestamp'] = datetime.now().isoformat()

        # Add tags and metadata if provided
        if tags:
            memory['tags'] = tags
        if metadata:
            memory['metadata'] = metadata

        # Add to short-term memory
        self.short_term.append(memory)

        # Prune short-term if needed
        if len(self.short_term) > self.max_short_term:
            removed = self.short_term.pop(0)
            logger.debug(f"Pruned short-term memory: {removed.get('task', {}).get('task', 'unknown')}")

        # Add to long-term memory
        self.long_term.append(memory)

        # Prune long-term if needed
        if len(self.long_term) > self.max_long_term:
            removed = self.long_term.pop(0)
            logger.debug(f"Pruned long-term memory: {removed.get('task', {}).get('task', 'unknown')}")

        # Persist to disk
        self._save_long_term()

        return memory['timestamp']

    def recall(
        self,
        query: str,
        limit: int = 10,
        phd_stage: Optional[str] = None,
        since: Optional[str] = None
    ) -> List[Dict]:
        """
        Recall relevant memories using keyword search

        Args:
            query: Search query string
            limit: Maximum number of results to return
            phd_stage: Optional filter by PhD stage
            since: Optional ISO timestamp to filter results after

        Returns:
            List of relevant memory entries
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Search in reverse chronological order (most recent first)
        for memory in reversed(self.long_term):
            # Check stage filter
            if phd_stage and memory.get('phd_stage') != phd_stage:
                continue

            # Check time filter
            if since:
                try:
                    memory_time = datetime.fromisoformat(memory.get('timestamp', ''))
                    filter_time = datetime.fromisoformat(since)
                    if memory_time < filter_time:
                        continue
                except (ValueError, TypeError):
                    pass

            # Keyword matching
            memory_str = json.dumps(memory, default=str).lower()
            match_score = 0

            # Count matching words
            for word in query_words:
                if word in memory_str:
                    match_score += 1

            # Boost score for exact phrase matches
            if query_lower in memory_str:
                match_score += len(query_words)

            if match_score > 0:
                memory_copy = memory.copy()
                memory_copy['_match_score'] = match_score
                results.append(memory_copy)

            if len(results) >= limit * 2:  # Get more than needed, then sort
                break

        # Sort by match score and limit results
        results.sort(key=lambda x: x.get('_match_score', 0), reverse=True)
        results = results[:limit]

        # Remove internal match_score
        for result in results:
            result.pop('_match_score', None)

        logger.debug(f"Recall found {len(results)} memories for query: {query[:50]}")
        return results

    def recall_by_task(
        self,
        task_name: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recall memories by task name

        Args:
            task_name: Name of the task to search for
            limit: Maximum number of results

        Returns:
            List of memories matching the task
        """
        results = []

        for memory in reversed(self.long_term):
            if memory.get('task', {}).get('task') == task_name:
                results.append(memory)
                if len(results) >= limit:
                    break

        logger.debug(f"Recall found {len(results)} memories for task: {task_name}")
        return results

    def recall_by_stage(
        self,
        phd_stage: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Recall all memories for a specific PhD stage

        Args:
            phd_stage: PhD stage to filter by
            limit: Maximum number of results

        Returns:
            List of memories from the specified stage
        """
        results = []

        for memory in reversed(self.long_term):
            if memory.get('phd_stage') == phd_stage:
                results.append(memory)
                if len(results) >= limit:
                    break

        logger.debug(f"Recall found {len(results)} memories for stage: {phd_stage}")
        return results

    def get_context(
        self,
        phd_stage: str,
        max_memories: int = 20,
        include_failed: bool = True
    ) -> str:
        """
        Get relevant context for current PhD stage

        Args:
            phd_stage: Current PhD stage
            max_memories: Maximum number of memories to include
            include_failed: Whether to include failed tasks

        Returns:
            JSON string of relevant memories
        """
        stage_memories = [
            m for m in self.long_term
            if m.get('phd_stage') == phd_stage
        ]

        # Filter out failed tasks if requested
        if not include_failed:
            stage_memories = [
                m for m in stage_memories
                if m.get('result', {}).get('success', False)
            ]

        # Get most recent memories
        recent_memories = reversed(stage_memories[-max_memories:])

        # Format for context
        context = []
        for memory in recent_memories:
            context_item = {
                'task': memory.get('task', {}).get('task', 'unknown'),
                'goal': memory.get('goal', ''),
                'timestamp': memory.get('timestamp', ''),
                'success': memory.get('result', {}).get('success', False)
            }
            context.append(context_item)

        return json.dumps(context, indent=2)

    def get_recent_activities(
        self,
        limit: int = 10,
        phd_stage: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recent activities from memory

        Args:
            limit: Maximum number of activities to return
            phd_stage: Optional filter by PhD stage

        Returns:
            List of recent activities
        """
        activities = []

        for memory in reversed(self.long_term):
            if phd_stage and memory.get('phd_stage') != phd_stage:
                continue

            activity = {
                'task': memory.get('task', {}).get('task', 'unknown'),
                'goal': memory.get('goal', ''),
                'timestamp': memory.get('timestamp', ''),
                'success': memory.get('result', {}).get('success', False),
                'stage': memory.get('phd_stage', 'unknown')
            }
            activities.append(activity)

            if len(activities) >= limit:
                break

        return activities

    def get_statistics(self) -> Dict:
        """
        Get memory statistics

        Returns:
            Dictionary with memory usage statistics
        """
        total_memories = len(self.long_term)
        successful_tasks = sum(
            1 for m in self.long_term
            if m.get('result', {}).get('success', False)
        )
        failed_tasks = total_memories - successful_tasks

        # Count by stage
        stage_counts = {}
        for memory in self.long_term:
            stage = memory.get('phd_stage', 'unknown')
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        # Count by task type
        task_counts = {}
        for memory in self.long_term:
            task = memory.get('task', {}).get('task', 'unknown')
            task_counts[task] = task_counts.get(task, 0) + 1

        return {
            'total_memories': total_memories,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': successful_tasks / total_memories if total_memories > 0 else 0,
            'short_term_count': len(self.short_term),
            'stage_distribution': stage_counts,
            'task_distribution': task_counts,
            'storage_path': str(self.path)
        }

    def clear_short_term(self):
        """Clear short-term memory"""
        self.short_term = []
        logger.info("Cleared short-term memory")

    def clear_long_term(self):
        """Clear long-term memory (with confirmation)"""
        self.long_term = []
        self._save_long_term()
        logger.warning("Cleared long-term memory")

    def export_memories(
        self,
        output_path: Optional[str] = None,
        format: str = 'json'
    ) -> str:
        """
        Export all memories to a file

        Args:
            output_path: Output file path (default: memory_export_TIMESTAMP.json)
            format: Export format ('json' or 'jsonl')

        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.path / f'memory_export_{timestamp}.{format}'
        else:
            output_path = Path(output_path)

        if format == 'jsonl':
            with open(output_path, 'w') as f:
                for memory in self.long_term:
                    f.write(json.dumps(memory) + '\n')
        else:  # json
            with open(output_path, 'w') as f:
                json.dump(self.long_term, f, indent=2)

        logger.info(f"Exported {len(self.long_term)} memories to {output_path}")
        return str(output_path)

    def import_memories(
        self,
        input_path: str,
        merge: bool = True
    ) -> int:
        """
        Import memories from a file

        Args:
            input_path: Path to import file
            merge: If True, merge with existing memories; if False, replace

        Returns:
            Number of imported memories
        """
        input_file = Path(input_path)

        if not input_file.exists():
            raise FileNotFoundError(f"Import file not found: {input_path}")

        imported_memories = []

        if input_file.suffix == '.jsonl':
            with open(input_file, 'r') as f:
                for line in f:
                    if line.strip():
                        imported_memories.append(json.loads(line))
        else:  # json
            with open(input_file, 'r') as f:
                imported_memories = json.load(f)

        if not merge:
            self.long_term = imported_memories
        else:
            # Merge, avoiding duplicates by timestamp
            existing_timestamps = {m.get('timestamp') for m in self.long_term}
            for memory in imported_memories:
                if memory.get('timestamp') not in existing_timestamps:
                    self.long_term.append(memory)
                    existing_timestamps.add(memory.get('timestamp'))

        self._save_long_term()
        logger.info(f"Imported {len(imported_memories)} memories from {input_path}")
        return len(imported_memories)

    def prune_old_memories(
        self,
        days: int = 365,
        keep_recent: int = 100
    ) -> int:
        """
        Remove old memories beyond a certain age

        Args:
            days: Maximum age in days to keep
            keep_recent: Always keep this many most recent memories

        Returns:
            Number of memories pruned
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        initial_count = len(self.long_term)

        # Sort by timestamp
        self.long_term.sort(key=lambda m: m.get('timestamp', ''))

        # Find cutoff index
        cutoff_index = len(self.long_term) - keep_recent
        cutoff_index = max(0, cutoff_index)

        # Remove old memories
        pruned = []
        new_memory = []

        for i, memory in enumerate(self.long_term):
            try:
                memory_date = datetime.fromisoformat(memory.get('timestamp', ''))
                if i >= cutoff_index or memory_date > cutoff_date:
                    new_memory.append(memory)
                else:
                    pruned.append(memory)
            except (ValueError, TypeError):
                # Keep memories with invalid timestamps
                new_memory.append(memory)

        self.long_term = new_memory
        self._save_long_term()

        logger.info(f"Pruned {len(pruned)} old memories (older than {days} days)")
        return len(pruned)

    def _load_long_term(self) -> None:
        """Load persistent memory from disk"""
        memory_file = self.path / 'long_term.json'

        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.long_term = json.load(f)

                # Ensure it's a list
                if not isinstance(self.long_term, list):
                    self.long_term = []

                logger.info(f"Loaded {len(self.long_term)} memories from disk")

            except Exception as e:
                logger.error(f"Error loading memories: {e}")
                self.long_term = []
        else:
            self.long_term = []

    def _save_long_term(self) -> None:
        """Save memory to disk"""
        memory_file = self.path / 'long_term.json'

        try:
            # Create temporary file first, then rename for atomicity
            temp_file = memory_file.with_suffix('.json.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.long_term, f, indent=2, ensure_ascii=False)

            # Rename to actual file
            temp_file.replace(memory_file)

        except Exception as e:
            logger.error(f"Error saving memories: {e}")

    def backup(self) -> str:
        """
        Create a backup of current memories

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.path / f'memory_backup_{timestamp}.json'

        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(self.long_term, f, indent=2)

        logger.info(f"Created backup at {backup_path}")
        return str(backup_path)

    def restore_backup(self, backup_path: str) -> int:
        """
        Restore memories from a backup

        Args:
            backup_path: Path to backup file

        Returns:
            Number of memories restored
        """
        backup_file = Path(backup_path)

        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with open(backup_file, 'r', encoding='utf-8') as f:
            self.long_term = json.load(f)

        self._save_long_term()
        logger.info(f"Restored {len(self.long_term)} memories from backup")
        return len(self.long_term)
