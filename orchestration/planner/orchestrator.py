"""
Research Orchestrator - Zero-Cost Pharma Research AI
Handles research planning and task decomposition with hybrid AI logic.
"""

import json
from typing import List, Optional
from dataclasses import dataclass

import requests
from pydantic import BaseModel, Field, model_validator

from modules.bio_ner.pubtator import PubTatorValidator
from modules.literature.semantic_scholar import SemanticScholarSearcher
from modules.compliance.academic_compliance import AcademicComplianceEngine

try:
    from modules.deep_drive.memory_engine import MemoryEngine

    HAS_MEMORY_ENGINE = True
except ImportError:
    MemoryEngine = None
    HAS_MEMORY_ENGINE = False


# =============================================================================
# Configuration Models
# =============================================================================

# =============================================================================
# Configuration Models
# =============================================================================


class OrchestratorConfig(BaseModel):
    """Configuration for the Research Orchestrator."""

    # 1. AI Provider Settings
    use_cloud_api: bool = Field(default=False)
    ollama_host: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="")
    cloud_api_url: Optional[str] = Field(default=None)
    cloud_api_key: Optional[str] = Field(default=None)

    # Expanded Provider Support
    primary_model: str = Field(default="google")
    google_key: Optional[str] = Field(default=None)
    openrouter_key: Optional[str] = Field(default=None)
    huggingface_key: Optional[str] = Field(default=None)
    glm_key: Optional[str] = Field(default=None)  # GLM-4.7

    # New Providers
    groq_key: Optional[str] = Field(default=None)
    groq_base_url: Optional[str] = Field(default=None)
    groq_model: Optional[str] = Field(default=None)
    deepseek_key: Optional[str] = Field(default=None)
    deepseek_base_url: Optional[str] = Field(default=None)
    deepseek_model: Optional[str] = Field(default=None)
    anthropic_key: Optional[str] = Field(default=None)

    # OpenRouter
    openrouter_base_url: Optional[str] = Field(default=None)
    openrouter_model: Optional[str] = Field(default=None)

    # HuggingFace
    huggingface_base_url: Optional[str] = Field(default=None)
    huggingface_model: Optional[str] = Field(default=None)

    # Specific Keys
    mistral_key: Optional[str] = Field(default=None)
    mistral_model: Optional[str] = Field(default=None)
    venice_key: Optional[str] = Field(default=None)
    venice_model: Optional[str] = Field(default=None)
    kimi_key: Optional[str] = Field(default=None)
    kimi_model: Optional[str] = Field(default=None)

    # Azure OpenAI
    azure_endpoint: Optional[str] = Field(default=None)
    azure_deployment: Optional[str] = Field(default=None)
    azure_key: Optional[str] = Field(default=None)
    azure_api_version: str = Field(default="2024-02-15-preview")

    # AWS Bedrock
    aws_access_key: Optional[str] = Field(default=None)
    aws_secret_key: Optional[str] = Field(default=None)
    aws_region_name: str = Field(default="us-east-1")
    aws_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")

    custom_key: Optional[str] = Field(default=None)
    custom_base_url: Optional[str] = Field(default=None)
    custom_model: str = Field(default="gpt-3.5-turbo")
    pubmed_email: Optional[str] = Field(default=None)

    # 2. Research Context (Section A)
    project_name: str = Field(default="My PhD Research")
    research_type: str = Field(default="PhD Thesis")
    disease_context: str = Field(default="General")
    research_stage: str = Field(default="Literature Review")

    # Advanced / Hardware
    performance_profile: str = Field(
        default="high", description="'high', 'moderate', or 'low'"
    )

    # 3. Agent AI Behavior (Section B)
    agent_mode: str = Field(default="semi-autonomous")
    reasoning_depth: str = Field(default="standard")
    self_correction: bool = Field(default=True)
    max_retries: int = Field(default=3)
    failure_policy: str = Field(default="ask_user")

    # 4. Literature Config (Section C)
    literature_sources: List[str] = Field(default=["pubmed", "europe_pmc"])
    year_range: int = Field(default=10)
    novelty_strictness: str = Field(default="medium")

    timeout: int = Field(default=30)

    # User Persona (Added for Perplexity-Like Logic)
    user_persona: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_api_keys(self) -> "OrchestratorConfig":
        """
        Auto-enable cloud API usage if keys are present and not explicitly disabled.
        Prioritizes Google > OpenRouter > Custom.
        """
        # Check if keys exist
        has_key = any(
            [self.google_key, self.openrouter_key, self.cloud_api_key, self.custom_key]
        )

        # Logic: If keys exist and use_cloud_api is False (default), flip it to True.
        # Check if keys exist
        # Note: If user explicitly passed use_cloud_api=False in init, Pydantic v2
        # doesn't easily track "set by user" vs "default" without extra logic.
        # But for this use case, presence of a key implies intent to use it.
        if has_key and not self.use_cloud_api:
            # We assume if you provide a key, you want to use it, unless you really force it off.
            # However, since false is default, we can't distinguish default vs explicit false easily.
            # We will flip to True as a "Smart Default".
            self.use_cloud_api = True

        # Resolve Primary Model based on keys if in 'auto' or default
        if self.use_cloud_api:
            if self.google_key and self.primary_model == "google":
                pass  # Good
            elif self.google_key:
                # If we have google key but model is generic, ensure google is used
                pass
            elif self.openrouter_key and not self.google_key:
                if self.primary_model == "google":  # Default
                    self.primary_model = "openrouter"

        return self


# =============================================================================
# Research Planning Models
# =============================================================================


class ResearchStep(BaseModel):
    """Individual step in a research plan."""

    step_id: int = Field(..., description="Unique step identifier")
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Detailed step description")
    category: str = Field(
        ...,
        description="Category: literature_search, entity_extraction, "
        "molecular_analysis, graph_building, etc.",
    )
    dependencies: List[int] = Field(
        default_factory=list, description="List of step IDs this step depends on"
    )
    estimated_time_minutes: Optional[int] = Field(
        default=None, description="Estimated time in minutes"
    )


class ResearchPlan(BaseModel):
    """Complete research plan with structured steps."""

    research_title: str = Field(..., description="Original research title")
    objectives: List[str] = Field(
        default_factory=list, description="Research objectives"
    )
    steps: List[ResearchStep] = Field(
        default_factory=list, description="Ordered research steps"
    )
    total_estimated_time_minutes: Optional[int] = Field(
        default=None, description="Total estimated time in minutes"
    )


# =============================================================================
# Research Orchestrator Class
# =============================================================================


class ResearchOrchestrator:
    """
    Orchestrates research planning and task decomposition.
    Supports hybrid AI logic: local Ollama or cloud API.
    """

    # Predefined research step categories
    STEP_CATEGORIES = [
        "literature_search",
        "entity_extraction",
        "molecular_analysis",
        "graph_building",
        "data_analysis",
        "synthesis_planning",
        "literature_review",
        "final_report",
    ]

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize the Research Orchestrator.
        Loads runtime configuration to determine Hybrid Mode (Cloud vs Local).
        """
        # 1. Load Runtime Config from Disk if not provided or incomplete
        from runtime.config_loader import load_config

        runtime_cfg = load_config()

        if config:
            self.config = config
        else:
            # BUILD FULL CONFIG FROM DISK
            # Mapping Settings Specification -> Orchestrator Config

            # Section A: Project
            project = runtime_cfg.get("project", {})

            # Section B: Agent
            agent = runtime_cfg.get("agent", {})

            # Section C: Literature
            lit = runtime_cfg.get("literature", {})

            # Section E: API & AI
            ai = runtime_cfg.get("ai_provider", {})

            # Use Agent Zero v1.9 as default - single mode
            self.config = OrchestratorConfig(
                # AI Settings
                use_cloud_api=True,
                # cloud_api_key removed (legacy)
                primary_model=ai.get("primary_model", "google"),
                google_key=ai.get("google_key"),
                openrouter_key=ai.get("openrouter_key"),
                huggingface_key=ai.get("huggingface_key"),
                glm_key=ai.get("glm_key"),  # Added GLM key mapping from runtime
                custom_key=ai.get("custom_key"),
                custom_base_url=ai.get("custom_base_url"),
                custom_model=ai.get("custom_model", "gpt-3.5-turbo"),
                pubmed_email=ai.get("pubmed_email"),
                # Context
                project_name=project.get("name", "PhD Research"),
                research_type=project.get("type", "Thesis"),
                disease_context=project.get("disease_context", "General"),
                research_stage=project.get("stage", "Review"),
                # Behavior
                agent_mode=agent.get("mode", "semi-autonomous"),
                reasoning_depth=agent.get("reasoning_depth", "standard"),
                self_correction=agent.get("self_correction", True),
                # Literature
                literature_sources=lit.get("sources", []),
                year_range=lit.get("year_range", 10),
                novelty_strictness=lit.get("novelty_strictness", "medium"),
                # Hardware Profile
                performance_profile=runtime_cfg.get("ai_advanced", {}).get(
                    "performance_profile", "high"
                ),
            )

        # Initialize Brain Components (Phase 2)
        self.pubtator = PubTatorValidator()
        self.scholar = SemanticScholarSearcher()
        self.compliance = AcademicComplianceEngine(
            strictness=self.config.novelty_strictness
        )

        if HAS_MEMORY_ENGINE:
            self.memory = MemoryEngine()
            print("[+] Deep Drive Memory Engine: Connected")
        else:
            self.memory = None
            print("[!] Deep Drive Memory Engine: Not available")

        if self.config.use_cloud_api and self.config.cloud_api_key:
            print(f"[+] Hybrid Mode Enabled: Using Cloud API")
        else:
            print(f"[*] Offline Mode: Using Local Ollama at {self.config.ollama_host}")

    # -------------------------------------------------------------------------
    # Main Planning Method
    # -------------------------------------------------------------------------

    async def plan_research(
        self, title: str, mode: str = "synthesize", task_id: Optional[str] = None
    ) -> ResearchPlan:
        """
        Decompose a research title into a structured research plan.
        Respects Mode Enforcement and Citation Lock rules.

        Args:
            title: Research title/topic
            mode: search | synthesize | write

        Returns:
            ResearchPlan with structured steps
        """

        async def _log(msg, type="thought"):
            if task_id:
                try:
                    from runtime.task_store import get_task_store

                    store = get_task_store()
                    await store.append_log(task_id, f"[{type.upper()}] {msg}")
                except:
                    pass

        await _log(f"Planning research strategy for: {title}", "thought")

        print(f"\n{'=' * 60}")
        print(f"Planning Research: {title} [Mode: {mode.upper()}]")
        print(f"{'=' * 60}")

        # 1. Mode Enforcement & Intent Check
        await _log(f"Enforcing mode: {mode.upper()}", "thought")
        if mode not in ["search", "synthesize", "write"]:
            await _log(f"Invalid mode {mode}, falling back to synthesize", "warn")
            mode = "synthesize"  # Fallback default

        # 2. Enrich Context (Phase 2 + Deep Drive)
        await _log(f"Retrieving cognitive context for: {title}", "thought")
        enriched_context = await self.enrich_context(title)

        # 3. Generate plan using configured AI backend
        await _log(
            f"Generating research steps using {self.config.primary_model}...", "thought"
        )
        import asyncio

        if self.config.use_cloud_api:
            # Hybrid is now async-capable
            plan_data = await self._generate_plan_hybrid(title, mode, enriched_context)
        else:
            # Local legacy is sync requests, wrap it
            plan_data = await asyncio.to_thread(
                self._generate_plan_local, title, mode, enriched_context
            )

        # Create ResearchPlan from generated data
        await _log(f"Structural analysis of research goal: {title}", "thought")
        plan = ResearchPlan(
            research_title=title,
            objectives=plan_data.get("objectives", []),
            steps=[ResearchStep(**step) for step in plan_data.get("steps", [])],
            total_estimated_time_minutes=plan_data.get("total_estimated_time"),
        )

        await _log(
            f"Plan constructed with {len(plan.steps)} steps and {len(plan.objectives)} objectives.",
            "thought",
        )

        # 4. Citation Lock / Novelty Gate (Logic Rule #2 & #4)
        strictness = self.config.user_persona.get("strictness", "balanced")
        if strictness == "conservative" and mode == "write":
            # For writing in conservative mode, we MUST have evidence first.
            # If this is a fresh start (step 1 is not verification), inject a gate.
            if plan.steps and "literature" not in plan.steps[0].category:
                print(
                    "[!] Citation Lock Enforced: Injecting mandatory verification step."
                )
                verification_step = ResearchStep(
                    step_id=0,
                    title="Mandatory Evidence Verification",
                    description="Verify existence of sufficient high-quality sources before drafting.",
                    category="literature_search",
                    dependencies=[],
                    estimated_time_minutes=15,
                )
                plan.steps.insert(0, verification_step)
                # Adjust IDs of subsequent steps
                for s in plan.steps[1:]:
                    s.step_id += 1
                    s.dependencies = [d + 1 for d in s.dependencies]
                    if s.step_id == 1:
                        s.dependencies.append(0)

        return plan

    def classify_intent(self, query: str) -> str:
        """
        Determines the research intent: discovery, review, or writing.
        """
        query_lower = query.lower()
        if any(
            x in query_lower for x in ["draft", "write", "report", "paper", "essay"]
        ):
            return "write"
        elif any(
            x in query_lower for x in ["compare", "review", "summary", "overview"]
        ):
            return "synthesize"  # Review mode
        elif any(
            x in query_lower for x in ["find", "search", "identify", "list", "new"]
        ):
            return "search"
        return "synthesize"  # Default to reasoning

    async def enrich_context(self, query: str) -> str:
        """
        Fetches 'Pharma-Grade' context to prime the LLM planner.
        Queries Semantic Scholar AND Cipher Memory.
        """
        context = []

        # 1. Semantic Scholar Impact Check
        try:
            papers = await asyncio.to_thread(
                self.scholar.search_impact_evidence, query, limit=3
            )
            if papers:
                titles = [
                    f"'{p['title']}' (Inf: {p['influentialCitationCount']})"
                    for p in papers
                ]
                context.append(f"Key Literature: {'; '.join(titles)}")
        except Exception as e:
            print(f"[!] Semantic Scholar context extraction failed: {e}")

        # 2. Deep Drive Memory (Native)
        if self.memory:
            try:
                # Search Memory
                memories = await self.memory.search_memory(query, top_k=3)
                if memories:
                    mem_text = "; ".join([m.get("text", "")[:100] for m in memories])
                    context.append(f"Internal Memory: {mem_text}")

                # Search Graph
                graph_data = await self.memory.search_graph(query, limit=5)
                if graph_data:
                    nodes = graph_data.get("nodes", [])
                    if nodes:
                        node_labels = [
                            n.get("labels", [])[0] if n.get("labels") else "Entity"
                            for n in nodes
                        ]
                        node_props = [
                            n.get("properties", {}).get("name", "Unknown")
                            for n in nodes
                        ]
                        graph_summary = ", ".join(
                            [f"{l}:{p}" for l, p in zip(node_labels, node_props)]
                        )
                        context.append(f"Knowledge Graph: {graph_summary}")

            except Exception as e:
                print(f"[!] Memory context extraction failed: {e}")

        return "\n".join(context)

    # -------------------------------------------------------------------------
    # Local Ollama Implementation
    # -------------------------------------------------------------------------

    def _generate_plan_local(self, title: str, mode: str, context: str = "") -> dict:
        """
        Generate research plan using local Ollama instance.
        """
        prompt = self._build_prompt(title, mode, context)

        try:
            response = requests.post(
                f"{self.config.ollama_host}/api/generate",
                json={
                    "model": self.config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            result = response.json()
            plan_text = result.get("response", "")

            # Parse the response
            plan_data = self._parse_plan_response(plan_text)

            return plan_data

        except requests.exceptions.Timeout:
            print("[!] Request timeout, using fallback plan")
            return self._generate_fallback_plan(title)
        except requests.exceptions.ConnectionError:
            print("[!] Connection error, using fallback plan")
            return self._generate_fallback_plan(title)
        except Exception as e:
            print(f"[!] Error generating plan: {e}")
            return self._generate_fallback_plan(title)

    def _build_prompt(
        self, title: str, mode: str = "synthesize", enriched_context: str = ""
    ) -> str:
        """
        Build the prompt for Ollama with Persona Injection AND Mode Enforcement.
        """
        # Extract Persona
        role = self.config.user_persona.get("role", "researcher").replace("_", " ")
        strictness = self.config.user_persona.get("strictness", "balanced")
        purpose = ", ".join(
            self.config.user_persona.get("primary_purpose", ["general"])
        )

        # Base Persona Instruction
        system_instruction = f"You are a pharmaceutical research planner acting as a senior assistant to a {role}."

        # MODE ENFORCEMENT (Logic Rule #3)
        mode_instruction = ""
        if mode == "search":
            mode_instruction = "MODE: SEARCH. Focus ONLY on retrieving, listing, and summarizing existing literature. Do not attempt synthesis or hypothesis generation yet."
        elif mode == "synthesize":
            mode_instruction = "MODE: SYNTHESIZE. Focus on connecting dot, building knowledge graphs, and identifying patterns across sources. Prioritize 'graph_building' and 'data_analysis' steps."
        elif mode == "write":
            mode_instruction = "MODE: WRITE. Focus on structuring a final specific output (review, report, or chapter). Ensure steps encompass outlining, drafting, and citation verification."

        # Strictness & Context
        if strictness == "conservative":
            system_instruction += (
                " You must be extremely rigorous. Avoid speculative steps."
            )
        elif strictness == "exploratory":
            system_instruction += (
                " You are encouraged to include novel, hypothesis-generating steps."
            )

        context_instruction = f"User Goal: {purpose}. {mode_instruction}"

        # LOGIC RULE #4: Conflict Detection (Plan B Requirement)
        context_instruction += "\nCRITICAL: You must actively look for and highlight CONTRADICTIONS or CONFLICTING EVIDENCE in the literature. Create specific steps to resolve these discrepancies."

        # Inject Enriched Data (Phase 2)
        if enriched_context:
            context_instruction += f"\n\nCONTEXT FROM DATABASE:\n{enriched_context}"

        prompt = f"""{system_instruction}
{context_instruction}

Create a detailed research plan for: "{title}"

Generate a plan with 4-8 steps strictly adhering to the {mode.upper()} mode.

Return JSON format:
{{
  "objectives": ["Objective 1", "Objective 2"],
  "steps": [
    {{
       "step_id": 1,
       "title": "Step Title",
       "description": "Actionable description",
       "category": "literature_search|entity_extraction|graph_building|data_analysis|synthesis_planning|literature_review|final_report",
       "dependencies": [],
       "estimated_time_minutes": 30
    }}
  ],
  "total_estimated_time": 120
}}

Provide ONLY the JSON."""

        return prompt

    def _parse_plan_response(self, response_text: str) -> dict:
        """
        Parse the AI response into plan data.

        Args:
            response_text: AI response text

        Returns:
            Parsed plan dictionary
        """
        try:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                plan_data = json.loads(json_str)
                return plan_data
            else:
                raise ValueError("No JSON found in response")

        except json.JSONDecodeError:
            print("⚠ Failed to parse JSON, using fallback plan")
            return self._generate_fallback_plan("Unknown Title")

    # -------------------------------------------------------------------------
    # Cloud API Implementation (Placeholder)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Hybrid API Implementation with Fallback Logic
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Hybrid API Implementation with Fallback Logic
    # -------------------------------------------------------------------------

    async def _generate_plan_hybrid(
        self, title: str, mode: str = "synthesize", context: str = ""
    ) -> dict:
        """
        Generate research plan using Cloud APIs with Fallback.
        Strategy: Primary -> Secondary -> Tertiary -> Local/Fallback
        """
        from modules.llm.factory import LLMFactory

        # 1. Define Priority Order
        available_providers = []

        # Add Primary First
        if self.config.primary_model in [
            "google",
            "openrouter",
            "huggingface",
            "zhipu",
            "custom",
            "lm_studio",
        ]:
            available_providers.append(self.config.primary_model)

        # Add others as backup
        candidates = [
            "google",
            "openrouter",
            "huggingface",
            "zhipu",
            "custom",
            "lm_studio",
        ]
        for c in candidates:
            if c != self.config.primary_model:
                available_providers.append(c)

        print(f"[*] Research Planner Strategy: {available_providers}")

        prompt = self._build_prompt(title, mode, context)

        for provider in available_providers:
            try:
                adapter = LLMFactory.get_adapter(provider, self.config)
                if not adapter:
                    continue

                print(f"[*] Attempting generation with: {provider.upper()}")

                # Call Adapter
                if hasattr(adapter, "async_generate"):
                    text_response = await adapter.async_generate(prompt)
                else:
                    text_response = await asyncio.to_thread(adapter.generate, prompt)

                # Parse
                plan = self._parse_plan_response(text_response)

                if plan:
                    print(f"[+] Successfully generated plan using {provider.upper()}")
                    return plan

            except Exception as e:
                print(f"[!] Provider {provider} failed: {e}")
                if "429" in str(e):
                    print(
                        f"⚠ Rate Limit Hit for {provider}. Switching to next provider..."
                    )
                continue

        print("[!] All cloud providers failed. Using offline fallback.")
        return self._generate_fallback_plan(title)

    # -------------------------------------------------------------------------
    # Fallback Plan Generation
    # -------------------------------------------------------------------------

    def _generate_fallback_plan(self, title: str) -> dict:
        """
        Generate a generic fallback plan when AI fails.
        """
        return {
            "objectives": [
                f"Conduct comprehensive literature review on {title}",
                "Extract relevant biomedical entities and relationships",
                "Analyze molecular structures and properties",
                "Generate actionable research insights",
            ],
            "steps": [
                {
                    "step_id": 1,
                    "title": "Literature Search",
                    "description": f"Search scientific databases for papers related to {title}",
                    "category": "literature_search",
                    "dependencies": [],
                    "estimated_time_minutes": 60,
                },
                {
                    "step_id": 2,
                    "title": "Entity Extraction",
                    "description": "Extract named entities (drugs, proteins, diseases) from literature",
                    "category": "entity_extraction",
                    "dependencies": [1],
                    "estimated_time_minutes": 45,
                },
                {
                    "step_id": 3,
                    "title": "Molecular Analysis",
                    "description": "Analyze molecular structures and chemical properties",
                    "category": "molecular_analysis",
                    "dependencies": [2],
                    "estimated_time_minutes": 90,
                },
                {
                    "step_id": 4,
                    "title": "Knowledge Graph Construction",
                    "description": "Build knowledge graph from extracted entities and relationships",
                    "category": "graph_building",
                    "dependencies": [2, 3],
                    "estimated_time_minutes": 60,
                },
                {
                    "step_id": 5,
                    "title": "Data Analysis",
                    "description": "Perform statistical and network analysis on research data",
                    "category": "data_analysis",
                    "dependencies": [4],
                    "estimated_time_minutes": 75,
                },
                {
                    "step_id": 6,
                    "title": "Literature Review",
                    "description": "Synthesize findings and generate comprehensive review",
                    "category": "literature_review",
                    "dependencies": [5],
                    "estimated_time_minutes": 90,
                },
                {
                    "step_id": 7,
                    "title": "Final Report Generation",
                    "description": "Generate final research report with insights and recommendations",
                    "category": "final_report",
                    "dependencies": [6],
                    "estimated_time_minutes": 60,
                },
            ],
            "total_estimated_time": 480,
        }

    # -------------------------------------------------------------------------
    # Self-Correction & Retry Logic (Agent Zero Pattern)
    # -------------------------------------------------------------------------

    def _validate_result(self, result: dict, task: dict, context: str = "") -> bool:
        """
        Validate task execution result using LLM reasoning.

        Args:
            result: The result from task execution
            task: The original task that was executed
            context: Additional context (e.g., phd_stage, research goal)

        Returns:
            True if result is valid and useful, False otherwise
        """
        # Quick checks first
        if not result:
            return False

        if isinstance(result, dict):
            if result.get("error") or result.get("success") == False:
                return False
            if not result.get("data") and not result.get("results"):
                return False

        # For literature search results, check if we got papers
        task_category = task.get("category", "")
        if "literature" in task_category or "search" in task_category:
            data = result.get("data", result.get("results", []))
            if isinstance(data, list) and len(data) == 0:
                print("[!] Validation: No results found in literature search")
                return False

        # For entity extraction, check if entities were found
        if "entity" in task_category or "extraction" in task_category:
            entities = result.get("entities", result.get("data", []))
            if not entities:
                print("[!] Validation: No entities extracted")
                return False

        return True

    def _adjust_task_params(
        self, task: dict, failed_result: dict, context: str = ""
    ) -> dict:
        """
        Use LLM to adjust task parameters after a validation failure.
        Implements the "rethinking" pattern from Agent Zero.

        Args:
            task: The task that failed validation
            failed_result: The result that failed validation
            context: Additional context for adjustment

        Returns:
            Adjusted task with modified parameters
        """
        from modules.llm.factory import LLMFactory

        adjusted_task = task.copy()
        params = adjusted_task.get("params", {})

        # Build adjustment prompt
        prompt = f"""A research task failed validation and needs adjustment.

ORIGINAL TASK:
- Category: {task.get("category", "unknown")}
- Title: {task.get("title", "unknown")}
- Parameters: {json.dumps(params, indent=2)}

FAILED RESULT:
{json.dumps(failed_result, indent=2)[:500]}

CONTEXT: {context}

Suggest ONE specific adjustment to the parameters to get better results.
Return ONLY a JSON object with the adjusted parameters, like:
{{"query": "adjusted query", "limit": 20, "year_range": 5}}

Focus on:
1. Broadening search terms if too specific
2. Narrowing if too broad (many irrelevant results)
3. Adjusting date ranges
4. Adding/removing filters
"""

        try:
            adapter = LLMFactory.get_adapter(self.config.primary_model, self.config)
            if adapter:
                response = adapter.generate(prompt)
                adjusted_params = self._parse_plan_response(response)
                if adjusted_params and isinstance(adjusted_params, dict):
                    adjusted_task["params"] = adjusted_params
                    print(f"[*] Self-correction: Adjusted params -> {adjusted_params}")
        except Exception as e:
            print(f"[!] Self-correction failed: {e}")
            # Fallback: broaden search if it looks like a search task
            if "query" in params:
                # Remove quotes and special chars to broaden
                original_query = params.get("query", "")
                adjusted_task["params"]["query"] = original_query.replace(
                    '"', ""
                ).split(" AND ")[0]
                print(f"[*] Fallback broadening: {adjusted_task['params']['query']}")

        return adjusted_task

    def execute_step_with_retry(
        self, step: "ResearchStep", max_retries: int = 3, context: str = ""
    ) -> dict:
        """
        Execute a research step with automatic retry and self-correction.

        Args:
            step: ResearchStep to execute
            max_retries: Maximum retry attempts
            context: Execution context (e.g., PhD stage)

        Returns:
            Dict with success status, data, and attempt history
        """
        task = {
            "category": step.category,
            "title": step.title,
            "description": step.description,
            "params": {},  # Would be populated from step details
        }

        attempts = []

        for attempt in range(max_retries):
            attempt_info = {"attempt": attempt + 1, "task": task.copy()}

            try:
                # Placeholder for actual tool execution
                # In real implementation, this would call the appropriate tool
                result = self._execute_step_tool(step, task.get("params", {}))

                # Validate result
                is_valid = self._validate_result(result, task, context)
                attempt_info["validated"] = is_valid

                if is_valid:
                    attempt_info["status"] = "success"
                    attempts.append(attempt_info)
                    return {
                        "success": True,
                        "data": result,
                        "attempts": attempts,
                        "step_title": step.title,
                    }
                else:
                    # Self-correction
                    print(f"[!] Attempt {attempt + 1} failed validation. Rethinking...")
                    task = self._adjust_task_params(task, result, context)
                    attempt_info["status"] = "validation_failed"
                    attempt_info["adjusted_task"] = task

            except Exception as e:
                print(f"[!] Attempt {attempt + 1} error: {e}")
                attempt_info["status"] = "error"
                attempt_info["error"] = str(e)

                if attempt < max_retries - 1:
                    task = self._adjust_task_params(task, {"error": str(e)}, context)

            attempts.append(attempt_info)

        return {
            "success": False,
            "error": "Max retries exceeded",
            "attempts": attempts,
            "step_title": step.title,
        }

    def _execute_step_tool(self, step: "ResearchStep", params: dict) -> dict:
        """
        Execute the appropriate tool for a research step.
        Placeholder for tool registry integration.
        """
        # This would be replaced with actual tool calls
        if "literature" in step.category:
            # Call literature search
            return self.scholar.search_impact_evidence(
                params.get("query", step.description), limit=params.get("limit", 10)
            )
        elif "entity" in step.category:
            # Call entity extraction
            return self.pubtator.validate_entities(params.get("text", step.description))
        else:
            # Generic execution
            return {"status": "executed", "step": step.title}


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Example 1: Using local Ollama
    print("\n=== Example 1: Local Ollama ===")
    config_local = OrchestratorConfig(
        use_cloud_api=False, ollama_host="http://localhost:11434", ollama_model=""
    )

    orchestrator = ResearchOrchestrator(config=config_local)
    plan = orchestrator.plan_research("Novel inhibitors for COVID-19 main protease")

    print(f"\nObjectives:")
    for obj in plan.objectives:
        print(f"  - {obj}")

    print(f"\nSteps:")
    for step in plan.steps:
        deps = f" (depends on: {step.dependencies})" if step.dependencies else ""
        print(f"  {step.step_id}. {step.title}{deps}")
        print(f"     Category: {step.category}")
        print(f"     Time: {step.estimated_time_minutes} min")

    print(f"\nTotal Estimated Time: {plan.total_estimated_time_minutes} minutes")

    # Example 2: Using cloud API (placeholder)
    print("\n\n=== Example 2: Cloud API (Placeholder) ===")
    config_cloud = OrchestratorConfig(
        use_cloud_api=True,
        cloud_api_url="https://api.example.com/research/plan",
        cloud_api_key="your-api-key-here",
    )

    orchestrator_cloud = ResearchOrchestrator(config=config_cloud)
    plan_cloud = orchestrator_cloud.plan_research(
        "Antibiotic resistance mechanisms in MRSA"
    )

    print(f"Generated {len(plan_cloud.steps)} steps for cloud API")
