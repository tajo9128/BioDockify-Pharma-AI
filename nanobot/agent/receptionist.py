"""
NanoBot Receptionist - The Front Desk of BioDockify AI.
Handles user interaction, intent classification, and delegation to the Boss (Agent Zero).
"""
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

from nanobot.agent.reasoning import ReasoningEngine
from nanobot.agent.working_memory import WorkingMemory
from nanobot.agent.memory import PersistentMemory
from nanobot.agent.context import ContextBuilder
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.utils.audit import AuditLogger
from nanobot.utils.broadcaster import StatusBroadcaster
from nanobot.agent.monitoring import ProgressMonitor
from nanobot.agent.planner_capabilities import ResearchPlannerCapabilities
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.web import WebSearchTool, BrowserTool
from nanobot.agent.tools.communication import EmailTool
from nanobot.agent.tools.calendar import CalendarTool
from nanobot.agent.tools.todoist import TaskTool
from nanobot.agent.tools.discord import DiscordTool
from nanobot.agent.intake_manager import ProjectIntakeManager
from nanobot.agent.validator_bridge import ValidatorBridge
from nanobot.supervisor.execution_supervisor import ExecutionSupervisor
from runtime.config_loader import load_config
from orchestration.planner.orchestrator import OrchestratorConfig

logger = logging.getLogger(__name__)

class NanoBotReceptionist:
    """
    The Receptionist Agent.
    - Lives at the "Front Desk" (Chat Interface).
    - Has its own Brain (ReasoningEngine + ContextBuilder).
    - Has its own Memory (PersistentMemory in nanobot subdir).
    - Can reply directly to small talk / simple queries.
    - Delegates complex tasks to Agent Zero (The Boss).
    """

    def __init__(self, agent_zero_instance=None):
        self.agent_zero = agent_zero_instance # "The Boss"
        
        # 1. Initialize Brain Config
        cfg = load_config()
        self.config = OrchestratorConfig(**self._map_config(cfg))
        
        # Setup Workspace & Own Memory
        self.workspace_root = Path("./data/workspace")
        self.my_workspace = self.workspace_root / "nanobot"
        self.my_workspace.mkdir(parents=True, exist_ok=True)
        
        # Initialize Audit Logger
        self.audit_logger = AuditLogger(self.my_workspace / "audit_log.jsonl")
        self.audit_logger.log_action("system_startup", {"version": "2.5.0"})
        
        # Initialize Broadcaster & Monitor
        self.broadcaster = StatusBroadcaster(cfg.get("notifications", {}))
        self.monitor = ProgressMonitor(self.broadcaster, project_root=str(self.workspace_root))
        self.monitor.start()
        
        # Phase 5: Intake, Validation & Supervisor
        self.intake = ProjectIntakeManager(self.workspace_root)
        self.validator = ValidatorBridge(self.workspace_root)
        self.supervisor = ExecutionSupervisor(check_interval=60)
        asyncio.create_task(self.supervisor.start())
        
        # Full Brain Components
        self.memory = PersistentMemory(self.my_workspace)
        self.context_builder = ContextBuilder(self.my_workspace) # Loads IDENTITY.md etc
        self.working_memory = WorkingMemory()
        
        # 2. Configure Native LiteLLMProvider
        api_key = None
        api_base = None
        model = self.config.custom_model
        
        # Robust Fallback Logic
        use_fallback = False
        
        if self.config.primary_model == "custom" or self.config.primary_model == "lm_studio":
            api_base = self.config.custom_base_url
            api_key = self.config.glm_key or "lm-studio"
            if model == "auto": model = "local-model"
            
        elif self.config.primary_model == "openrouter":
            if not self.config.openrouter_key:
                logger.warning("NanoBot: OpenRouter key missing. Falling back to LM Studio.")
                use_fallback = True
            else:
                api_key = self.config.openrouter_key
                model = self.config.custom_model
                if not model or model == "auto": model = "anthropic/claude-3-haiku"
            
        elif self.config.primary_model == "ollama":
            api_base = self.config.ollama_host
            model = self.config.custom_model
            
        elif self.config.primary_model == "google":
             if not self.config.google_key:
                 logger.warning("NanoBot: Google key missing. Falling back to LM Studio.")
                 use_fallback = True
             else:
                 api_key = self.config.google_key
                 model = "gemini/gemini-pro"
                 
        if use_fallback:
            self.config.primary_model = "lm_studio"
            api_base = "http://localhost:1234/v1"
            api_key = self.config.glm_key or "lm-studio"
            model = "local-model"

        self.provider = LiteLLMProvider(
            api_key=api_key,
            api_base=api_base,
            default_model=model
        )
        
        # 3. Initialize Reasoning Engine
        self.brain = ReasoningEngine(provider=self.provider)
        self.history = []
        
        # 4. Strategic Planner Capabilities
        self.planner = ResearchPlannerCapabilities(self.brain, project_root=str(self.my_workspace))
        
        # 5. Define Receptionist Tools
        
        ask_boss_tool = {
            "type": "function",
            "function": {
                "name": "ask_boss",
                "description": "Delegate a complex research or system task to Agent Zero (The Boss). Use this for anything requiring research, coding, or deep analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "A clear, concise summary of what the user wants Agent Zero to do."
                        }
                    },
                    "required": ["task_description"]
                }
            }
        }

        craft_title_tool = {
            "type": "function",
            "function": {
                "name": "craft_research_title",
                "description": "Generate high-impact academic titles from a research spark or topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The research idea or spark."}
                    },
                    "required": ["prompt"]
                }
            }
        }

        design_methodology_tool = {
            "type": "function",
            "function": {
                "name": "design_methodology",
                "description": "Convert a vague research idea into a structured methodology and validate feasibility.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "spark": {"type": "string", "description": "The research idea."}
                    },
                    "required": ["spark"]
                }
            }
        }

        bootstrap_project_tool = {
            "type": "function",
            "function": {
                "name": "bootstrap_project",
                "description": "Professional project onboarding. Creates workspace structure and seeds project context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "goal": {"type": "string"},
                        "researcher_role": {"type": "string"}
                    },
                    "required": ["project_name", "goal", "researcher_role"]
                }
            }
        }

        validate_output_tool = {
            "type": "function",
            "function": {
                "name": "validate_research_output",
                "description": "Sanity check code scripts or data schema integrity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "type": {"type": "string", "enum": ["python_script", "csv_schema"]},
                        "required_headers": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["file_path", "type"]
                }
            }
        }

        register_heartbeat_tool = {
            "type": "function",
            "function": {
                "name": "register_execution_heartbeat",
                "description": "Register a heartbeat for an active research task to NanoBot supervisor.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "task_type": {"type": "string"},
                        "status": {"type": "string", "enum": ["running", "blocked", "completed", "error"]},
                        "progress_percent": {"type": "number"},
                        "activity_state": {"type": "string"}
                    },
                    "required": ["task_id", "task_type", "status", "progress_percent", "activity_state"]
                }
            }
        }

        evaluate_strategy_tool = {
            "type": "function",
            "function": {
                "name": "evaluate_research_strategy",
                "description": "Perform a strategic risk and resource evaluation for a planned methodology.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "methodology": {"type": "string", "description": "The research plan/methodology to evaluate."}
                    },
                    "required": ["methodology"]
                }
            }
        }

        freeze_state_tool = {
            "type": "function",
            "function": {
                "name": "freeze_reproducibility_snapshot",
                "description": "Capture a reproducibility-grade snapshot of the current project state (tools, data checksums, versions).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "A label for this snapshot (e.g., 'Pre-Simulation', 'Initial Draft')."},
                        "project_metadata": {"type": "object", "description": "Key parameters or settings to include in the snapshot."}
                    },
                    "required": ["label", "project_metadata"]
                }
            }
        }
        
        consult_manual_tool = {
            "type": "function",
            "function": {
                "name": "consult_manual",
                "description": "Check the internal manual/docs for quick answers about BioDockify capabilities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        }
        
        # Instantiate Skills
        msg_tool = MessageTool()
        if self.agent_zero and hasattr(self.agent_zero, "bus"):
             msg_tool.set_send_callback(self.agent_zero.bus.push_outbound)
             
        browser_tool = BrowserTool()
        email_tool = EmailTool()
        web_search_tool = WebSearchTool() # Brave Search
        
        # External Skills
        calendar_tool = CalendarTool()
        todoist_tool = TaskTool()
        discord_tool = DiscordTool()

        self.tools = [
            ask_boss_tool,
            craft_title_tool,
            design_methodology_tool,
            bootstrap_project_tool,
            validate_output_tool,
            register_heartbeat_tool,
            evaluate_strategy_tool,
            freeze_state_tool,
            consult_manual_tool,
            msg_tool.to_schema(),
            browser_tool.to_schema(),
            email_tool.to_schema(),
            web_search_tool.to_schema(),
            calendar_tool.to_schema(),
            todoist_tool.to_schema(),
            discord_tool.to_schema()
        ]

    def _map_config(self, raw_cfg: dict) -> dict:
        """Map raw dict config to OrchestratorConfig dict."""
        ai = raw_cfg.get("ai_provider", {})
        return {
            "primary_model": ai.get("mode", "lm_studio"),
            "google_key": ai.get("google_key"),
            "openrouter_key": ai.get("openrouter_key"),
            "ollama_host": ai.get("ollama_host") or "http://localhost:11434",
            "custom_base_url": ai.get("lm_studio_url") or "http://localhost:1234/v1",
            "custom_model": ai.get("lm_studio_model") or "auto",
            "glm_key": ai.get("glm_key")
        }

    async def process_chat(self, message: str) -> str:
        """
        Main entry point for user messages.
        NanoBot decides: Reply or Delegate?
        """
        logger.info(f"NanoBot Receptionist received: {message}")
        
        # 1. Update History
        self.history.append({"role": "user", "content": message})
        
        # 2. Build Context
        system_prompt = self.context_builder.build_system_prompt(working_memory=self.working_memory)
        
        # Append specific Receptionist Instructions on top of Identity
        system_prompt += """
\n
## RECEPTIONIST PROTOCOL
1.  **GREET & FILTER**: Respond to greetings/questions yourself.
2.  **USE SKILLS**: You have tools for Browsing, Emailing, and Messaging. Use them if requested.
3.  **DELEGATE DEEP WORK**: If the user asks for Research, Coding, or Analysis -> Use `ask_boss`.
4.  **REPORT**: Summarize the Boss's results to the user.
"""

        # 3. Think
        response_text, tool_calls, _ = await self.brain.think(
            goal="Handle User Message",
            system_prompt=system_prompt,
            history=self.history,
            working_memory=self.working_memory,
            tools=self.tools
        )
        
        # 4. Handle Content
        final_reply = response_text or ""
        
        # 5. Handle Tool Calls
        if tool_calls:
            for call in tool_calls:
                call_result = ""
                
                # Delegation
                if call.name == "ask_boss":
                    task = call.arguments.get("task_description")
                    logger.info(f"Delegate to Boss: {task}")
                    if not final_reply:
                        final_reply = f"I'll ask Agent Zero to handle that: '{task}'"
                    
                    if self.agent_zero:
                        boss_reply = await self.agent_zero.run_task(task)
                        final_reply += f"\n\n**Agent Zero:**\n{boss_reply}"
                        # Store result
                        await self.memory.store({
                            "content": f"Boss completed task: {task}", 
                            "result": boss_reply[:200], 
                            "type": "delegation"
                        })
                    else:
                        final_reply += "\n\n(Error: Agent Zero is not in the office.)"
                        
                # Local Skills (Browser, Email, Message, Search)
                elif call.name in ["browser_automation", "send_email", "message", "web_search", "consult_manual", "craft_research_title", "design_methodology", "evaluate_research_strategy", "freeze_reproducibility_snapshot"]:
                    logger.info(f"NanoBot executing skill: {call.name}")
                    if not final_reply:
                        final_reply = f"Executing {call.name}..."
                    
                    # Execute locally via self.tools list lookup? 
                    # We need to dispatch. reasoning.py might return tool calls but doesn't auto-execute?
                    # NanoBot needs a mini-dispatcher.
                    
                    # Dispatch
                    tool_instance = None
                    # Find tool instance if possible (names mismatch with schema slightly requiring logic)
                    # For now, simplistic mapping or re-instantiation?
                    # Better: map name to function/instance.
                    
                    try:
                        result = await self._execute_local_skill(call.name, call.arguments)
                        final_reply += f"\n\n**Tool Result ({call.name}):**\n{result}"
                    except Exception as e:
                         final_reply += f"\n\n(Tool Failure: {e})"

        self.history.append({"role": "assistant", "content": final_reply})
        
        if len(final_reply) > 20: 
             await self.memory.store({"content": f"User: {message}\nMe: {final_reply}", "type": "chat"})
             
        return final_reply

    async def _execute_local_skill(self, name: str, args: dict) -> str:
        """Execute local NanoBot skills."""
        if name == "browser_automation":
            tool = BrowserTool()
            return await tool.execute(**args)
        elif name == "send_email":
            # Lazy import to avoid circular defaults if needed, but we imported at top
            tool = EmailTool()
            return await tool.execute(**args)
        elif name == "message":
            tool = MessageTool()
            if self.agent_zero and hasattr(self.agent_zero, "bus"):
                tool.set_send_callback(self.agent_zero.bus.push_outbound)
            return await tool.execute(**args)
        elif name == "web_search":
            tool = WebSearchTool()
            return await tool.execute(**args)
        elif name == "consult_manual":
            return "Manual consult feature pending implementation."
        
        # Strategic Planner Skills
        elif name == "craft_research_title":
            return await self.planner.craft_title(args.get("prompt"), self.working_memory)
        elif name == "design_methodology":
            res = await self.planner.design_methodology(args.get("spark"), self.working_memory)
            return res.get("methodology", "Failed to generate methodology.")
        elif name == "evaluate_research_strategy":
            res = await self.planner.evaluate_strategy(args.get("methodology"), self.working_memory)
            return json.dumps(res, indent=2)
        elif name == "freeze_reproducibility_snapshot":
            snap_id = await self.planner.freeze_project_state(
                label=args.get("label"), 
                project_metadata=args.get("project_metadata"), # legacy support
                dataset_path=args.get("dataset_path"),
                parameters=args.get("parameters"),
                workflow_state=args.get("workflow_state"),
                outputs=args.get("outputs")
            )
            return f"Reproducibility Snapshot Created: {snap_id}"
        elif name == "bootstrap_project":
            res = await self.intake.bootstrap_workspace(args.get("project_name"), args.get("researcher_role"))
            await self.intake.seed_project_context(args.get("project_name"), args.get("goal"))
            return f"Project '{args.get('project_name')}' bootstrapped successfully. Context seeded."
        elif name == "validate_research_output":
            ftype = args.get("type")
            if ftype == "python_script":
                res = self.validator.validate_python_script(args.get("file_path"))
            else:
                res = self.validator.validate_data_schema(args.get("file_path"), args.get("required_headers", []))
            return json.dumps(res, indent=2)
        elif name == "register_execution_heartbeat":
            from nanobot.models.heartbeat_schema import Heartbeat
            from datetime import datetime, timezone
            hb = Heartbeat(
                task_id=args.get("task_id"),
                task_type=args.get("task_type"),
                status=args.get("status"),
                progress_percent=float(args.get("progress_percent")),
                activity_state=args.get("activity_state"),
                timestamp=datetime.now(timezone.utc)
            )
            await self.supervisor.register_heartbeat(hb)
            return f"Heartbeat registered for task {args.get('task_id')}."
        
        # External Skills
        elif name == "calendar":
            tool = CalendarTool()
            return await tool.execute(**args)
        elif name == "todoist":
            tool = TaskTool()
            return await tool.execute(**args)
        elif name == "discord_tool":
            tool = DiscordTool()
            return await tool.execute(**args)
            
        return f"Unknown tool: {name}"
