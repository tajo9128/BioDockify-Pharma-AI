"""
Device State Manager - Handles device awareness and session management
Features:
- Track device state (on/off)
- Session management
- Auto-stop/start based on device state
- Progress persistence
- Context restoration
"""
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class DeviceState(str, Enum):
    """Device states"""
    ONLINE = "online"
    OFFLINE = "offline"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"


@dataclass
class DeviceSession:
    """Represents a device session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    state: DeviceState = DeviceState.ACTIVE
    active_tasks: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectContext:
    """Context for a specific project"""
    project_id: str
    task_states: Dict[str, Dict[str, Any]]  # task_id -> state data
    current_phase: str
    last_position: str
    scroll_position: int
    form_data: Dict[str, Any]
    annotations: List[Dict[str, Any]]
    device_sessions: List[DeviceSession] = field(default_factory=list)


class DeviceStateManager:
    """
    Device State Manager
    
    Features:
    - Track device online/offline state
    - Manage sessions
    - Save/restore context
    - Auto-suspend inactive sessions
    - Resume on reconnection
    """

    def __init__(self, memory_system=None):
        self.memory_system = memory_system
        self.current_device_id = None
        self.current_session: Optional[DeviceSession] = None
        self.project_contexts: Dict[str, ProjectContext] = {}
        self.active_projects: List[str] = []
        self.device_heartbeat_interval = 30  # seconds
        self.idle_timeout = 300  # 5 minutes idle timeout
        self._heartbeat_task = None
        self._idle_monitor_task = None
        self._setup_logging()

    def _setup_logging(self):
        logger.info("Device State Manager initialized")

    async def initialize(self, device_id: str):
        """Initialize device state manager"""
        self.current_device_id = device_id
        logger.info(f"Device State Manager initialized for device: {device_id}")

        # Restore previous sessions from memory
        await self._restore_sessions()

        # Start heartbeat and idle monitoring
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._idle_monitor_task = asyncio.create_task(self._idle_monitor_loop())

        # Set device state to online
        await self._set_device_state(DeviceState.ONLINE)

    async def _set_device_state(self, state: DeviceState):
        """Update device state"""
        if self.current_session:
            self.current_session.state = state

        # Store in memory
        if self.memory_system:
            from modules.memory.advanced_memory import MemoryType, MemoryImportance

            state_content = f"""
Device State Changed
Device ID: {self.current_device_id}
New State: {state.value}
Timestamp: {datetime.utcnow().isoformat()}
Active Tasks: {len(self.active_projects)}
            """.strip()

            await self.memory_system.add_memory(
                content=state_content,
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.MEDIUM,
                source="device_manager",
                tags=['device_state', state.value, str(self.current_device_id)]
            )

        logger.info(f"Device state set to: {state.value}")

    async def create_session(self, project_id: str) -> DeviceSession:
        """Create a new device session for a project"""
        # Ensure we have a device ID
        device_id = self.current_device_id or "default_device"
        
        session = DeviceSession(
            device_id=device_id,
            active_tasks=[project_id],
            context={"current_project": project_id}
        )

        self.current_session = session
        if project_id not in self.active_projects:
            self.active_projects.append(project_id)

        # Store session in memory
        await self._store_session(session)

        await self._set_device_state(DeviceState.ACTIVE)

        logger.info(f"Created session for project: {project_id}")
        return session

    async def end_session(self, session_id: str):
        """End a session"""
        if self.current_session and self.current_session.session_id == session_id:
            self.current_session.end_time = datetime.utcnow()

            # Remove active projects
            for project_id in self.current_session.active_tasks:
                if project_id in self.active_projects:
                    self.active_projects.remove(project_id)

            # Save session to memory
            await self._store_session(self.current_session)

            await self._set_device_state(DeviceState.IDLE)

            logger.info(f"Ended session: {session_id}")

    async def _store_session(self, session: DeviceSession):
        """Store session in persistent memory"""
        if not self.memory_system:
            return

        try:
            from modules.memory.advanced_memory import MemoryType, MemoryImportance

            session_content = f"""
Session ID: {session.session_id}
Device ID: {session.device_id}
Start Time: {session.start_time.isoformat()}
End Time: {session.end_time.isoformat() if session.end_time else 'In Progress'}
State: {session.state.value}
Active Tasks: {len(session.active_tasks)}
Context: {str(session.context)}
            """.strip()

            await self.memory_system.add_memory(
                content=session_content,
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.HIGH,
                source=f"session:{session.session_id}",
                tags=['session', 'device', str(session.device_id), session.state.value],
                metadata={
                    'session_id': session.session_id,
                    'device_id': session.device_id,
                    'start_time': session.start_time.isoformat(),
                    'end_time': session.end_time.isoformat() if session.end_time else None,
                    'active_tasks': session.active_tasks,
                    'context': session.context
                }
            )

        except Exception as e:
            logger.error(f"Error storing session: {e}")

    async def _restore_sessions(self):
        """Restore previous sessions from memory"""
        if not self.memory_system:
            return

        try:
            from modules.memory.advanced_memory import MemoryType

            # Search for recent sessions
            results = await self.memory_system.search(
                query="session device",
                limit=10
            )

            logger.info(f"Restored {len(results)} sessions from memory")

        except Exception as e:
            logger.error(f"Error restoring sessions: {e}")

    async def save_project_context(
        self,
        project_id: str,
        context_data: Dict[str, Any]
    ):
        """Save project context (form data, scroll position, annotations, etc.)"""
        context = ProjectContext(
            project_id=project_id,
            task_states=context_data.get('task_states', {}),
            current_phase=context_data.get('current_phase', 'planning'),
            last_position=context_data.get('last_position', ''),
            scroll_position=context_data.get('scroll_position', 0),
            form_data=context_data.get('form_data', {}),
            annotations=context_data.get('annotations', [])
        )

        self.project_contexts[project_id] = context

        # Store in persistent memory
        if self.memory_system:
            from modules.memory.advanced_memory import MemoryType, MemoryImportance

            context_content = f"""
Project Context Saved
Project ID: {project_id}
Phase: {context.current_phase}
Last Position: {context.last_position}
Scroll Position: {context.scroll_position}
Form Fields: {len(context.form_data)} fields
Annotations: {len(context.annotations)} items
            """.strip()

            await self.memory_system.add_memory(
                content=context_content,
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.MEDIUM,
                source=f"project_context:{project_id}",
                tags=['project_context', project_id, 'state_saved'],
                metadata={
                    'project_id': project_id,
                    'context_data': context_data
                }
            )

        logger.info(f"Saved context for project: {project_id}")

    async def restore_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Restore project context from memory"""
        if project_id in self.project_contexts:
            return self.project_contexts[project_id]

        # Try to restore from memory
        if self.memory_system:
            try:
                results = await self.memory_system.search(
                    query=f"project context {project_id}",
                    limit=1
                )

                if results:
                    # In a real impl, we'd parse the metadata
                    # We'll simulate restoration from the first result's metadata
                    memory = results[0]
                    metadata = memory.get('metadata', {})
                    context_data = metadata.get('context_data', {})
                    
                    if context_data:
                        context = ProjectContext(
                            project_id=project_id,
                            task_states=context_data.get('task_states', {}),
                            current_phase=context_data.get('current_phase', 'planning'),
                            last_position=context_data.get('last_position', ''),
                            scroll_position=context_data.get('scroll_position', 0),
                            form_data=context_data.get('form_data', {}),
                            annotations=context_data.get('annotations', [])
                        )
                        self.project_contexts[project_id] = context
                        logger.info(f"Restored context for project: {project_id} from memory")
                        return context

            except Exception as e:
                logger.error(f"Error restoring context: {e}")

        return None

    async def _heartbeat_loop(self):
        """Periodic heartbeat to track device activity"""
        while True:
            try:
                await asyncio.sleep(self.device_heartbeat_interval)

                # Update heartbeat
                if self.current_session:
                    # Store heartbeat in memory
                    await self._store_session(self.current_session)

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def _idle_monitor_loop(self):
        """Monitor device idle time and auto-suspend"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Check for idle timeout
                if self.current_session and self.current_session.state == DeviceState.IDLE:
                    idle_time = (datetime.utcnow() - self.current_session.start_time).total_seconds()

                    if idle_time > self.idle_timeout:
                        logger.info(f"Idle timeout reached, suspending device")
                        await self._set_device_state(DeviceState.SUSPENDED)

            except asyncio.CancelledError:
                logger.info("Idle monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Idle monitor loop error: {e}")

    async def suspend(self):
        """Suspend current session and stop background tasks"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._idle_monitor_task:
            self._idle_monitor_task.cancel()

        # Save all active project contexts
        for project_id in self.active_projects:
            if project_id in self.project_contexts:
                await self.save_project_context(project_id, asdict(self.project_contexts[project_id]))

        await self._set_device_state(DeviceState.SUSPENDED)

        logger.info("Device suspended")

    async def resume(self):
        """Resume from suspended state"""
        await self._set_device_state(DeviceState.ACTIVE)

        # Restart background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._idle_monitor_task = asyncio.create_task(self._idle_monitor_loop())

        logger.info("Device resumed")

    async def get_device_status(self) -> Dict[str, Any]:
        """Get current device status"""
        return {
            "device_id": self.current_device_id,
            "state": self.current_session.state.value if self.current_session else "unknown",
            "session_id": self.current_session.session_id if self.current_session else None,
            "active_projects": self.active_projects,
            "last_heartbeat": self.current_session.start_time.isoformat() if self.current_session else None,
            "idle_time": (datetime.utcnow() - self.current_session.start_time).total_seconds() if self.current_session else 0
        }

    async def get_active_project_contexts(self) -> Dict[str, Any]:
        """Get contexts of all active projects"""
        return {
            project_id: asdict(self.project_contexts[project_id])
            for project_id in self.active_projects
            if project_id in self.project_contexts
        }


# Global instance
_device_state_manager: Optional[DeviceStateManager] = None


def get_device_state_manager(memory_system=None) -> DeviceStateManager:
    """Get or create global device state manager instance"""
    global _device_state_manager
    if _device_state_manager is None:
        _device_state_manager = DeviceStateManager(memory_system=memory_system)
    return _device_state_manager
