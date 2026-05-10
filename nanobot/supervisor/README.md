# NanoBot — Execution Supervisor & Activity Watchdog

This module provides a task-agnostic, adaptive, and scalable supervision layer for Agent Zero within the BioDockify ecosystem. It ensures that research tasks proceed as expected and intervenes when activity stalls or goes silent.

## 🏗️ Architecture

- **`ExecutionSupervisor`**: The main orchestrator that runs the supervision loop and ties all modules together.
- **`HeartbeatMonitor`**: Tracks structured heartbeats and detects simple time-based silence or stalls.
- **`VelocityAnalyzer`**: Computes progress velocity (Δprogress / Δtime) to detect subtle performance degradation.
- **`EscalationEngine`**: Manages a 6-level progressive escalation protocol (Healthy -> user alert -> restart suggestion).
- **`TaskProfileManager`**: Loads task-adaptive policies (e.g., higher patience for ML training vs. writing tasks).
- **`AuditLogger`**: Maintains an immutable, append-only `audit_log.jsonl` of all supervisor actions.

## 🚦 Escalation Levels

| Level | Name | Description |
| :--- | :--- | :--- |
| **0** | Healthy | Normal operation detected. |
| **1** | Soft Reminder | Periodic liveness check request. |
| **2** | Direct Prompt | Request for state clarification from the agent. |
| **3** | Diagnostic Request | Forcing the agent to run a self-check. |
| **4** | User Notification | Alerting the human researcher of a potential stall. |
| **5** | Restart Suggestion | Recommending a task reset or terminal intervention. |

## 📦 Heartbeat Schema

Heartbeats are sent via Pydantic model with the following mandatory fields:
- `task_id`: Unique identifier.
- `task_type`: Profile type (e.g., `writing`, `ml_training`).
- `status`: One of `running`, `blocked`, `waiting_input`, `completed`, `error`.
- `progress_percent`: 0-100 float.
- `activity_state`: Descriptive string of current work.
- `timestamp`: UTC datetime.

## 🚀 Usage

```python
from nanobot.supervisor.execution_supervisor import ExecutionSupervisor
from nanobot.models.heartbeat_schema import Heartbeat

# Initialize (runs every 60s by default)
supervisor = ExecutionSupervisor(check_interval=60)
await supervisor.start()

# Feed heartbeats from Agent Zero
hb = Heartbeat(
    task_id="bio_research_01",
    task_type="ml_training",
    status="running",
    progress_percent=45.5,
    activity_state="Training epoch 12...",
    timestamp=datetime.now(timezone.utc)
)
await supervisor.register_heartbeat(hb)
```

## 🔐 Safety Constraints
NanoBot supervisor **monitors only**. It is strictly forbidden from executing research logic, modifying task parameters, or performing heavy computation. Its sole purpose is to ensure the **Executive (Agent Zero)** remains healthy and productive.
