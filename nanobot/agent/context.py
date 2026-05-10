"""Context builder for assembling agent prompts."""

import base64
import mimetypes
import platform
from pathlib import Path
from typing import Any

from nanobot.agent.memory import PersistentMemory
from nanobot.agent.skills import SkillsLoader


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.
    
    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = PersistentMemory(workspace)
        self.skills = SkillsLoader(workspace)
    
    def build_system_prompt(self, skill_names: list[str] | None = None, working_memory: Any = None) -> str:
        """
        Build the system prompt from bootstrap files, memory, skills, and working memory.
        
        Args:
            skill_names: Optional list of skills to include.
            working_memory: Optional WorkingMemory object to provide reasoning context.
        
        Returns:
            Complete system prompt.
        """
        parts = []
        
        # Core identity
        parts.append(self._get_identity())
        
        # Working Memory (Brain state)
        if working_memory:
            parts.append(f"# Internal Working Memory\n\n{working_memory.format_for_prompt()}")
        
        # Bootstrap files
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # Memory context
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        # Skills - progressive loading
        # 1. Always-loaded skills: include full content
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # 2. Available skills: only show summary (agent uses read_file to load)
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

{skills_summary}""")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """Get the core identity section."""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# BioDockify AI Lite (NanoBot) 🧬

You are **BioDockify AI Lite**, the autonomous Research Operations Manager and Strategic Architect for the BioDockify ecosystem.
While you possess deep technical capabilities, your primary mission is to structure, supervise, and validate research workflows, ensuring they are scientifically rigorous and reproducible.

You have access to POWERFUL tools that allow you to:
- **Strategically Plan**: Design methodologies, craft titles, and evaluate research risks.
- **Onboard & Bootstrap**: Manage workspace intake and project context.
- **Supervise Execution**: Monitor heartbeats and progress velocity of research tasks.
- **Validate & Gate**: Sanity check code/data and manage human-in-the-loop approvals.
- **Ensure Reproducibility**: Capture multi-layer SRSE snapshots and protect against drift.

## Your Mission
1. **Perfect Receptionist & Architect**:
   - Act as the primary interface for users.
   - Onboard projects by bootstrappping workspaces and seeding context.
   - Guide users through the research lifecycle (Student, Faculty, Researcher personas).
2. **Operations Supervisor**:
   - Monitor the health and progress of **BioDockify AI Hybrid (Agent Zero)**.
   - Intervene and escalate if execution stalls or communication heartbeats go silent.
3. **Scientific Gatekeeper**:
   - Validate research outputs for syntax, schema, and integrity before finalization.
   - Maintain the audit trail for every significant research event.

## Team Structure
- **BioDockify AI Lite (You)**: The strategic overseer, operations manager, and user receptionist.
- **BioDockify AI Hybrid (Agent Zero)**: The "Deep Research" and "Heavy Coding" executor (The Boss).
  - You delegate complex execution tasks to the Hybrid core using the `ask_boss` tool.

## Current Time
{now}

## Runtime
{runtime}

## Workspace
Your operations workspace is at: {workspace_path}
- Persistent Memory: {workspace_path}/memory/MEMORY.md
- Audit Trail: {workspace_path}/audit_log.jsonl
- Reproducibility Snapshots: {workspace_path}/.reproducibility/snapshots/

## System Instructions
- **Proactivity**: When asked to fix a configuration or debug a service, USE YOUR TOOLS (`read_file`, `write_file`, `execute_command`) to resolve it directly.
- **Direct Response**: For conversational queries, reply directly with text.
- **Messaging**: Use the `message` tool ONLY when communicating via a specific external channel (Telegram, WhatsApp, etc.).
- **Memory**: Write significant research findings or user preferences to `{workspace_path}/memory/MEMORY.md`.
"""
    
    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        working_memory: Any = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages.
            current_message: The new user message.
            skill_names: Optional skills to include.
            media: Optional list of local file paths for images/media.
            channel: Current channel (telegram, whatsapp, etc.).
            chat_id: Current chat/user ID.
            working_memory: Optional WorkingMemory object.

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # System prompt
        system_prompt = self.build_system_prompt(skill_names, working_memory)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text
        
        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        
        if not images:
            return text
        return images + [{"type": "text", "text": text}]
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        Add a tool result to the message list.
        
        Args:
            messages: Current message list.
            tool_call_id: ID of the tool call.
            tool_name: Name of the tool.
            result: Tool execution result.
        
        Returns:
            Updated message list.
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Add an assistant message to the message list.
        
        Args:
            messages: Current message list.
            content: Message content.
            tool_calls: Optional tool calls.
        
        Returns:
            Updated message list.
        """
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        messages.append(msg)
        return messages
