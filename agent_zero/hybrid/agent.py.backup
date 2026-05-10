"""
Hybrid Agent Core - The Brain of BioDockify AI
Combines:
1. Agent Zero's monologue loop (continuous reasoning)
2. NanoBot's tools & skills
3. SurfSense's research capabilities
4. Unified LLM Interface (LM Studio/API)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, List, Optional

from nanobot.models.heartbeat_schema import Heartbeat

from modules.llm.factory import LLMFactory
from orchestration.planner.orchestrator import OrchestratorConfig
from agent_zero.hybrid.context import AgentContext, AgentConfig, LoopData
from agent_zero.hybrid.memory import HybridMemory, MemoryArea
from agent_zero.hybrid.prompts import get_system_prompt
from agent_zero.hybrid.diagnosis import SystemDiagnosis
from agent_zero.hybrid.tools.code_execution import SafeCodeExecutionTool
from agent_zero.hybrid.tools.file_editor import FileEditorTool
from agent_zero.hybrid.tools.config_tool import ConfigManagerTool
from agent_zero.hybrid.tools.graph_tool import KnowledgeGraphTool
from agent_zero.hybrid.tools.github_tool import GitHubTool
from agent_zero.skills.reviewer_agent import get_reviewer_agent
from agent_zero.skills.achademio.wrapper import get_achademio
from agent_zero.skills.latte_review.wrapper import get_latte_review
from agent_zero.skills.deep_drive.wrapper import get_deep_drive
from agent_zero.skills.scholar_copilot.wrapper import get_scholar_copilot
from agent_zero.skills.email_messenger import get_email_messenger
from agent_zero.skills.browser_scraper import get_browser_scraper
from modules.headless_research.engine import deep_research as stealth_deep_research
from agent_zero.hybrid.errors import RepairableException, InterventionException, format_error
from agent_zero.hybrid.bus import MessageBus, OutboundMessage, InboundMessage
from agent_zero.services.cron import CronService

logger = logging.getLogger(__name__)

class HybridAgent:
    """
    BioDockify Hybrid Agent (Agent Zero + NanoBot + SurfSense).
    Integrates:
    - Self-Awareness (Agent Zero Monologue)
    - Communications (NanoBot MessageBus)
    - Researcher (SurfSense)
    """
    
    def __init__(self, config: AgentConfig, llm_config: OrchestratorConfig):
        self.config = config
        self.context = AgentContext(config=config)
        self.memory = HybridMemory(config.workspace_path, config.memory_subdir)
        self.on_heartbeat: Optional[Callable[[Heartbeat], Coroutine[Any, Any, None]]] = None
        
        # Unified LLM Interface
        self.llm_adapter = LLMFactory.get_adapter(
            provider=llm_config.primary_model, 
            config=llm_config
        )
        if not self.llm_adapter:
            raise ValueError(f"Failed to initialize LLM adapter for provider: {llm_config.primary_model}")
            
        # --- NanoBot Core Integrations ---
        self.bus = MessageBus()
        self.cron = CronService(config.workspace_path, self._handle_external_trigger)
        
        # Initialize Tools (Robustly)
        self.tools = {}
        
        def safe_init(name: str, init_func: Callable) -> Optional[Any]:
            try:
                return init_func()
            except Exception as e:
                logger.warning(f"⚠️ Tool '{name}' failed to load: {e}. Running in degraded mode.")
                return None

        # Core Tools
        self.diagnosis = safe_init("SystemDiagnosis", lambda: SystemDiagnosis())
        self.code_exec = safe_init("SafeCodeExecutionTool", lambda: SafeCodeExecutionTool())
        self.file_editor = safe_init("FileEditorTool", lambda: FileEditorTool(root_dir="."))
        self.config_manager = safe_init("ConfigManagerTool", lambda: ConfigManagerTool())
        self.graph_tool = safe_init("KnowledgeGraphTool", lambda: KnowledgeGraphTool())
        
        # GitHub Tool (Dynamic injection)
        github_token = getattr(llm_config, "github_token", None)
        self.github = safe_init("GitHubTool", lambda: GitHubTool(token=github_token))

        # Register Available Tools
        if self.diagnosis:
            self.tools["diagnosis"] = self.diagnosis.get_diagnosis_report
            
        if self.code_exec:
            self.tools["execute_shell"] = self.code_exec.execute_shell
            self.tools["execute_python"] = self.code_exec.execute_python
            
        if self.file_editor:
            self.tools["read_file"] = self.file_editor.read_file
            self.tools["write_file"] = self.file_editor.write_file
            self.tools["replace_in_file"] = self.file_editor.replace_in_file
            
        if self.config_manager:
            self.tools["get_config"] = self.config_manager.get_config
            self.tools["update_config"] = self.config_manager.update_config
            
        if self.graph_tool:
            self.tools["graph_query"] = self.graph_tool.query_graph
            self.tools["graph_schema"] = self.graph_tool.get_schema
            self.tools["graph_add_node"] = self.graph_tool.add_node

        if self.github:
            self.tools["github_search"] = self.github.search_repositories
            self.tools["github_read"] = self.github.get_repo_content
            self.tools["github_issue"] = self.github.create_issue

        # Skills (Lazy Safe Load)
        self.tools.update({
            "spawn_agent": self._spawn_subagent,
            "send_message": self._tool_send_message,
            "manage_cron": self._tool_manage_cron,
            "deep_research": self._tool_deep_research,
            
            # Wrappers that are already safe or lazy
            "verify_citations": get_reviewer_agent().verify_citations,
            "academic_rewrite": lambda p: get_achademio().rewrite_academic(p.get("text")),
            "academic_slides": lambda p: get_achademio().text_to_slides(p.get("text")),
            "academic_proofread": lambda p: get_achademio().proofread(p.get("text")),
            
            "latte_screen": lambda p: get_latte_review().screen_papers(
                p.get("input_path"), 
                p.get("inclusion"), 
                p.get("exclusion"), 
                p.get("output_path")
            ),
            "latte_score": lambda p: get_latte_review().score_papers(
                p.get("input_path"), 
                p.get("scoring_task") or p.get("task"), 
                p.get("scoring_set") or p.get("set", [0,1,2]), 
                p.get("scoring_rules") or p.get("rules"), 
                p.get("output_path")
            ),
            
            "send_email": lambda p: get_email_messenger().send_email(
                p.get("to"), p.get("subject"), p.get("body"), p.get("attachments")
            ),
            "notify_user": lambda p: get_email_messenger().notify_user(
                p.get("email"), p.get("message"), p.get("channels"), p.get("file")
            ),
            
            "browse_stealth": self._tool_browse_stealth,
            "browse_general": self._tool_browse_general,
            "browse_pdf": self._tool_browse_pdf,
            
            "deep_drive_analyze": lambda p: get_deep_drive().analyze_authorship(p.get("text"), p.get("task", "clef24")),
            "scholar_complete": lambda p: get_scholar_copilot().complete_text(p.get("text")),
            "summarize_content": self._tool_summarize_content,
            "report_progress": self._tool_report_progress,
            "declare_task": self._tool_declare_task
        })
        
        self.skills = {} # Will load skills later
        
        # State
        self.loop_data = LoopData()
        self.is_running = False
        self._channels_started = False
        self.repair_attempts = {} # Track repairs per error
        self.max_repairs_per_error = 3
        
        # Internal Supervision state
        self._current_progress = 0.0
        self._current_task_type = "general"
        self._current_task_id = "initialization"

    async def _handle_external_trigger(self, message: str):
        """Handle input from Cron or Channels."""
        await self.bus.push_inbound(InboundMessage(content=message, source="system_trigger"))

    async def _tool_send_message(self, params: dict) -> str:
        """Tool to send message via MessageBus."""
        content = params.get("content")
        target = params.get("target") or "discord"
        chat_id = params.get("chat_id")
        if not content or not chat_id: return "Error: 'content' and 'chat_id' parameters are required"
        
        await self.bus.push_outbound(OutboundMessage(content=content, target=target, chat_id=chat_id))
        return "Message queued for delivery."

    async def _tool_manage_cron(self, params: dict) -> str:
        """Tool to manage cron jobs."""
        action = params.get("action", "list")
        if action == "add":
            return self.cron.add_job(params["name"], params["schedule"], params["instruction"])
        elif action == "remove":
            return self.cron.remove_job(params["job_id"])
        return self.cron.list_jobs()

    async def start_services(self):
        """Start background services (Bus, Cron, Channels)."""
        if self._channels_started: return
        
        await self.bus.start()
        await self.cron.start()
        self._channels_started = True

    async def stop_services(self):
        await self.bus.stop()
        await self.cron.stop()

    async def _spawn_subagent(self, params: dict) -> str:
        task = params.get("task")
        label = params.get("label", "subagent")
        if not task: return "Error: 'task' parameter is required"
        
        try:
            from agent_zero.enhanced import get_agent_zero_enhanced
            return await get_agent_zero_enhanced().spawn_background_task(task, label)
        except Exception as e:
            return f"Failed to spawn agent: {str(e)}"

    async def _tool_deep_research(self, params: dict) -> str:
        """
        Conduct deep research using SurfSense options.
        Pipeline: Plan -> Search -> Crawl -> Curate -> Reason -> Ingest Materials.
        """
        query = params.get("query")
        if not query: return "Error: 'query' parameter is required"
        
        try:
            # 1. Imports (Lazy to avoid circular deps if any)
            from agent_zero.web_research import (
                SearchPlanner, SearchQuery, SurfSense, Executor, 
                Curator, Reasoner, CrawlConfig, CuratorConfig
            )
            
            # 2. Plan
            planner = SearchPlanner()
            search_query = SearchQuery(question=query)
            # Simple source planning (default to PubMed/Wiki for now)
            sources = planner.recommend_sources(search_query) 
            
            # 3. Construct Search URLs (Simple Mapping for Demo)
            start_urls = []
            for source in sources:
                if source == "PubMed":
                    start_urls.append(f"https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ', '+')}")
                elif source == "Wikipedia":
                    start_urls.append(f"https://en.wikipedia.org/w/index.php?search={query.replace(' ', '+')}")
                elif source == "Google Scholar":
                    # Note: Scholar often challenges bots, but we include it per planner
                    start_urls.append(f"https://scholar.google.com/scholar?q={query.replace(' ', '+')}")
            
            if not start_urls:
                start_urls = [f"https://google.com/search?q={query.replace(' ', '+')}"]

            # 4. Crawl (SurfSense)
            executor = Executor()
            surfsense = SurfSense()
            crawl_config = CrawlConfig(
                urls=start_urls,
                rules=surfsense.create_default_rules(),
                depth=1, # Keep shallow for speed in demo
                max_pages=5
            )
            
            results = await surfsense.crawl(crawl_config, executor)
            
            # 5. Curate (Save to Disk)
            curator = Curator(config=CuratorConfig(base_path=f"{self.config.workspace_path}/web_research"))
            await curator.save_results(results, query)
            
            # 6. Reason (Synthesize Answer)
            reasoner = Reasoner()
            reasoner.set_llm_adapter(self.llm_adapter)
            answer_obj = await reasoner.synthesize_answer(query, results)
            answer_text = reasoner.format_answer_with_citations(answer_obj)
            
            # --- Hardening: Save to Memory (Bug #4) ---
            await self.memory.add_memory(
                f"Deep research completed for query: {query}\n"
                f"Synthesized Answer: {answer_obj.answer}\n"
                f"Sources: {len(results)} crawled.",
                area=MemoryArea.MAIN
            )
            
            # --- [ENHANCED] Material Ingestion (Bug #80) ---
            try:
                from modules.library.store import library_store
                import mimetypes
                
                materials_found = 0
                for res in results:
                    url = res.url.lower()
                    title = res.title or "Untitled Research Source"
                    
                    # 1. Detect PDFs (Papers/Books)
                    if url.endswith(".pdf") or "pdf" in res.metadata.get("content_type", ""):
                        logger.info(f"Ingesting scientific paper: {url}")
                        raw_data = res.metadata.get("raw_data")
                        
                        if raw_data:
                            # Save actual PDF binary
                            library_store.add_file(
                                raw_data,
                                f"{title.replace(' ', '_')[:50]}.pdf",
                                meta={"type": "paper", "source_url": res.url, "query": query, "format": "pdf"}
                            )
                        else:
                            # Fallback to text archive
                            file_content = f"# Paper archive: {title}\nSource: {res.url}\n\n{res.content}"
                            library_store.add_file(
                                file_content.encode("utf-8"), 
                                f"{title.replace(' ', '_')[:50]}.md", 
                                meta={"type": "paper", "source_url": res.url, "query": query, "format": "md_archive"}
                            )
                        materials_found += 1
                        
                    # 2. Detect Videos
                    elif any(v in url for v in ["youtube.com", "vimeo.com", "video"]):
                        logger.info(f"Ingesting video material stub: {url}")
                        video_record = f"# Video Material: {title}\nURL: {res.url}\n\nDescription summary from search:\n{res.content[:500]}..."
                        library_store.add_file(
                            video_record.encode("utf-8"),
                            f"video_{hashlib.md5(url.encode()).hexdigest()[:8]}.md",
                            meta={"type": "video", "source_url": res.url, "query": query}
                        )
                        materials_found += 1
                
                if materials_found > 0:
                    logger.info(f"Successfully ingested {materials_found} research materials into the library.")
            except Exception as material_err:
                logger.error(f"Failed to ingest materials: {material_err}")

            # --- Hardening: Bridge to RAG for Notebook (Bug #10 glue) ---
            try:
                from modules.rag.ingestor import ingestor
                from modules.rag.vector_store import get_vector_store
                from modules.library.store import library_store
                
                # Save answer as a research report in the library
                filename = f"tool_research_{hashlib.md5(query.encode()).hexdigest()}.md"
                content = f"# Research: {query}\n\n{answer_text}"
                record = library_store.add_file(content.encode("utf-8"), filename, meta={"tool_call": "deep_research", "query": query, "type": "research_report"})
                
                # Ingest for notebook
                file_path = library_store.get_file_path(record['id'])
                chunks = ingestor.ingest_file(str(file_path))
                if chunks:
                    await get_vector_store().add_documents(chunks)
                    logger.info(f"Research result indexed into RAG: {len(chunks)} chunks")
            except Exception as bridge_err:
                logger.error(f"Failed to bridge tool research to RAG: {bridge_err}")
            
            return answer_text
            
        except Exception as e:
            logger.error(f"Deep Research Failed: {e}")
            return f"Deep research failed: {str(e)}"
        


    async def _tool_browse_stealth(self, params: dict) -> str:
        """Tool for stealthy deep research browsing."""
        url = params.get("url")
        if not url: return "Error: url required"
        # Using the imported async function from modules.headless_research
        res = await stealth_deep_research(url)
        # Check status and return formatted string
        if res.get("status") == "success":
            content = res.get("content", "")
            return f"Stealth Browse Successful.\nTitle: {res.get('title')}\nLength: {len(content)}\n\n{content[:2000]}...\n[Content Truncated]"
        return f"Stealth Browse Failed: {res.get('error')}"

    async def _tool_browse_general(self, params: dict) -> str:
        """Tool for general browser scraping (non-stealth or login-based)."""
        url = params.get("url")
        wait_for = params.get("wait_for", "body")
        if not url: return "Error: 'url' parameter is required"
        
        # Get singleton and run
        scraper = get_browser_scraper()
        res = await scraper.scrape_page(url, wait_for)
        
        if res.get("success"):
            content = res.get("content", "")
            return f"Browse Successful.\nTitle: {res.get('title')}\nLength: {len(content)}\n\n{content[:2000]}...\n[Content Truncated]"
        return f"Browse Failed: {res.get('error')}"

    async def _tool_browse_pdf(self, params: dict) -> str:
        """Tool to download PDF."""
        url = params.get("url")
        if not url: return "Error: url required"
        
        scraper = get_browser_scraper()
        path = await scraper.download_pdf(url)
        
        if path:
            return f"PDF Downloaded Successfully to: {path}"
        return "PDF Download Failed."

    async def _tool_summarize_content(self, params: dict) -> str:
        """Native summarization using the agent's LLM."""
        text = params.get("text")
        url = params.get("url")
        
        content_to_summarize = text
        if url:
            # If URL provided, try to scrape it first
            if not content_to_summarize:
                res = await self._tool_browse_general({"url": url})
                content_to_summarize = res
        
        if not content_to_summarize:
            return "Error: 'text' or 'url' parameters are required"
            
        prompt = f"Please provide a concise summary of the following content:\n\n{content_to_summarize[:10000]}"
        return await self.llm_adapter.generate(prompt)

    async def _tool_report_progress(self, params: dict) -> str:
        """Tool for the agent to explicitly report research progress."""
        progress = params.get("percent")
        task_id = params.get("task_id") or self._current_task_id
        task_type = params.get("task_type") or self._current_task_type
        message = params.get("message", "Progress update")

        if progress is not None:
            try:
                self._current_progress = float(progress)
            except ValueError:
                return "Error: progress must be a number"

        if task_id: self._current_task_id = task_id
        if task_type: self._current_task_type = task_type

        await self._emit_heartbeat(status="running", activity=message)
        return f"Progress reported: {self._current_progress}% for task {self._current_task_id}"

    async def _tool_declare_task(self, params: dict) -> str:
        """Tool to formally declare task metadata before execution."""
        task_id = params.get("task_id")
        task_type = params.get("task_type")
        
        if not task_id or not task_type:
            return "Error: 'task_id' and 'task_type' are required for task declaration."
            
        self._current_task_id = task_id
        self._current_task_type = task_type
        self._current_progress = 0.0
        
        # Store metadata for heartbeat context
        self.loop_data.data["task_metadata"] = params
        
        await self._emit_heartbeat(status="running", activity=f"Task Declared: {task_id}")
        return f"Task {task_id} declared successfully. Ready for execution."

    async def _emit_heartbeat(self, status: str = "running", activity: str = "Idle"):
        """Emit a structured heartbeat for the supervisor."""
        if not self.on_heartbeat:
            return

        # Ensure we have a valid task_id
        task_id = self._current_task_id or "idle"
        
        hb = Heartbeat(
            task_id=task_id,
            task_type=self._current_task_type,
            status=status,
            progress_percent=self._current_progress,
            activity_state=activity,
            timestamp=datetime.now(timezone.utc)
        )
        
        try:
            await self.on_heartbeat(hb)
        except Exception as e:
            logger.error(f"Failed to emit heartbeat: {e}")

    async def monologue(self):
        """
        The Core Loop (Agent Zero Style).
        Continuous reasoning cycle until task completion or pause.
        Supports Self-Healing and User Intervention.
        """
        self.is_running = True
        logger.info(f"Agent {self.config.name} starting monologue loop...")
        
        while self.is_running:
            try:
                # 1. Prepare Context (History, Memory, Skills)
                prompt = await self._build_prompt()
                
                # 2. Call LLM (Reasoning)
                response = await self.llm_adapter.generate(prompt)
                
                # 3. Process Response (Tool Calls vs Answer)
                if self._is_tool_call(response):
                    try:
                        # Extract tool name for activity state
                        activity = f"Executing tool: {response[:50]}..."
                        await self._emit_heartbeat(status="running", activity=activity)
                        
                        result = await self._execute_tool(response)
                        await self.memory.add_memory(f"Tool Result: {result}", area=MemoryArea.FRAGMENTS)
                        self.loop_data.history.append({"role": "system", "content": f"Tool Output: {result}"})
                    except Exception as e:
                        # Wrap tool errors as Repairable to trigger fix
                        raise RepairableException(f"Tool execution failed: {str(e)}")
                else:
                    # Final answer or conversation
                    self.loop_data.last_response = response
                    self.loop_data.history.append({"role": "assistant", "content": response})
                    
                    # Store important insights
                    if len(response) > 50:
                        await self.memory.add_memory(response, area=MemoryArea.MAIN)
                        
                    # Pause loop to wait for user if just chatting
                    if not self._has_pending_tasks():
                         self.is_running = False

            except RepairableException as e:
                err_str = str(e)
                attempts = self.repair_attempts.get(err_str, 0)
                
                if attempts >= self.max_repairs_per_error:
                    logger.error(f"Max repair attempts reached for error: {err_str}")
                    self.loop_data.history.append({"role": "system", "content": f"FATAL: Max repair attempts ({self.max_repairs_per_error}) reached for: {err_str}. Please intervene."})
                    self.is_running = False
                    continue

                self.repair_attempts[err_str] = attempts + 1
                logger.warning(f"Self-Healing Triggered (Attempt {attempts + 1}/{self.max_repairs_per_error}): {e}")
                err_msg = format_error(e)
                # Feed error back into history to prompt a fix
                self.loop_data.history.append({
                    "role": "system", 
                    "content": f"CRITICAL ERROR: {err_msg}\nYou must fix this error in your next step."
                })
                # Loop continues immediately to let LLM try again
                
            except InterventionException:
                logger.info("User intervention received. Pausing.")
                self.is_running = False
                
            except Exception as e:
                logger.error(f"Fatal error in monologue: {e}")
                self.loop_data.history.append({"role": "system", "content": f"Fatal System Error: {str(e)}"})
                self.is_running = False
                raise e
                
    async def execute(self, prompt: str) -> str:
        """Execution entry point for TaskManager."""
        self.loop_data.user_message = prompt
        self.loop_data.history.append({"role": "system", "content": f"Task Execution Triggered: {prompt}"})
        
        # Start/Resume loop
        await self.monologue()
        
        return self.loop_data.last_response

    async def chat(self, user_message: str):
        """Entry point for user interaction."""
        self.loop_data.user_message = user_message
        self.loop_data.history.append({"role": "user", "content": user_message})
        
        # Start/Resume loop
        await self.monologue()
        
        return self.loop_data.last_response

    async def _build_prompt(self) -> str:
        """Construct the prompt from context, memory, and history."""
        
        # Performance Pruning
        if self.config.performance_profile == "low":
            # Low Resource Mode: Only last 3 messages
            history_slice = self.loop_data.history[-3:]
        elif self.config.performance_profile == "moderate":
            # Moderate Resource Mode: Last 6 messages (4k context)
            history_slice = self.loop_data.history[-6:]
        else:
            # High Resource Mode: Last 10 messages
            history_slice = self.loop_data.history[-10:]
            
        history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history_slice])
        
        # Semantic Memory Recall
        query = self.loop_data.user_message or (self.loop_data.history[-1]['content'] if self.loop_data.history else "")
        memories = []
        if query:
            memories = await self.memory.search(query, limit=3)
        
        memory_text = "\n".join([f"- {m['content']} (Score: {m['score']:.2f})" for m in memories]) if memories else "None"

        system = f"{get_system_prompt()}\n"
        system += f"Workspace: {self.config.workspace_path}\n"
        system += f"Recent Activity Context:\n{self.memory.get_recent(1)}\n"
        system += f"Relevant Semantic Memory:\n{memory_text}\n"
        system += f"Tools Available: {list(self.tools.keys())}\n"
        
        return f"{system}\n\nConversation:\n{history_text}\n\n{self.config.name}:"

    def _is_tool_call(self, response: str) -> bool:
        """
        Check if response requests a tool execution.
        Looks for JSON format or explicit tool: markers.
        """
        response_lower = response.lower()
        if "{" in response and "tool" in response_lower:
            return True
        return any(marker in response_lower for marker in ["tool:", "call:", "execute:"])

    async def _execute_tool(self, response: str) -> str:
        """
        Execute a requested tool using robust parsing.
        Supports both legacy string-based and modern JSON-based tool calls.
        """
        tool_name = None
        params = {}

        # 1. Try JSON Parsing (Robust)
        try:
            import re
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                tool_name = data.get("tool") or data.get("task") or data.get("call")
                params = data.get("params") or data.get("args") or {}
                # If tool_name is None, it might be structured like {"tool_name": {...params}}
                if not tool_name and len(data) == 1:
                    tool_name = list(data.keys())[0]
                    params = data[tool_name]
        except Exception:
            pass

        # 2. Fallback to String Parsing (Legacy)
        if not tool_name:
            for marker in ["tool:", "call:", "execute:"]:
                if marker in response.lower():
                    # Format: "tool: tool_name parameters..."
                    parts = response.split(marker, 1)[1].strip().split(None, 1)
                    tool_name = parts[0].strip(": \n")
                    if len(parts) > 1:
                        params = {"input": parts[1].strip()}
                    break

        if not tool_name:
            return "Error: Could not parse tool name from response."

        # 3. Execution Dispatch
        logger.info(f"HybridAgent: Executing tool '{tool_name}' with params: {params}")
        
        # Normalize tool name
        tool_name = tool_name.lower().replace("_", "")
        
        # Check registered tools
        for registered_name, func in self.tools.items():
            if registered_name.lower().replace("_", "") == tool_name:
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(params)
                    else:
                        result = func(params)
                    return str(result)
                except Exception as e:
                    logger.error(f"Tool execution failed ({tool_name}): {e}")
                    return f"Error executing {tool_name}: {str(e)}"

        return f"Error: Tool '{tool_name}' not found. Available: {list(self.tools.keys())}"

    def _has_pending_tasks(self) -> bool:
        return False

# Factory to create the unified agent
def create_hybrid_agent(workspace: str = "./data/workspace") -> HybridAgent:
    from orchestration.planner.orchestrator import OrchestratorConfig
    from runtime.config_loader import load_config
    
    # Load real config from Settings
    cfg = load_config()
    ai_config = cfg.get("ai_provider", {})
    
    mode = ai_config.get("mode", "openai")
    
    # Map settings to OrchestratorConfig
    llm_config = OrchestratorConfig(
        primary_model=mode,
        # Map common fields for LLMFactory
        openai_key=ai_config.get("openai_key"),
        anthropic_key=ai_config.get("anthropic_key"),
        google_key=ai_config.get("google_key"),
        groq_key=ai_config.get("groq_key"),
        openrouter_key=ai_config.get("openrouter_key"),
        deepseek_key=ai_config.get("deepseek_key"),
        
        # Extended Providers
        mistral_key=ai_config.get("mistral_key"),
        mistral_model=ai_config.get("mistral_model"),
        venice_key=ai_config.get("venice_key"),
        venice_model=ai_config.get("venice_model"),
        kimi_key=ai_config.get("kimi_key"),
        kimi_model=ai_config.get("kimi_model"),

        # Azure OpenAI
        azure_endpoint=ai_config.get("azure_endpoint"),
        azure_deployment=ai_config.get("azure_deployment"),
        azure_key=ai_config.get("azure_key"),
        azure_api_version=ai_config.get("azure_api_version", "2024-02-15-preview"),

        # AWS Bedrock
        aws_access_key=ai_config.get("aws_access_key"),
        aws_secret_key=ai_config.get("aws_secret_key"),
        aws_region_name=ai_config.get("aws_region_name", "us-east-1"),
        aws_model_id=ai_config.get("aws_model_id"),
        
        # Custom/Local fields
        custom_base_url=ai_config.get("custom_base_url") or ai_config.get("lm_studio_url") or "http://localhost:1234/v1",
        custom_model=ai_config.get("custom_model") or ai_config.get("lm_studio_model") or "auto",
        custom_key=ai_config.get("custom_key"),
        
        # Ollama
        ollama_host=ai_config.get("ollama_host") or "http://localhost:11434",
        ollama_model=ai_config.get("ollama_model") or "llama2"
    )
    
    # Ensure attributes exist for LLMFactory if OrchestratorConfig doesn't have them
    # custom_base_url and custom_model are already mapped above for LM Studio usage

    
    agent_config = AgentConfig(
        name="BioDockify AI",
        workspace_path=workspace,
        performance_profile=cfg.get("ai_advanced", {}).get("performance_profile", "high")
    )
    
    return HybridAgent(agent_config, llm_config)
