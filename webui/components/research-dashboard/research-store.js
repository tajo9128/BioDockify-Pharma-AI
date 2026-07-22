import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("researchDashboard", {
  activeTab: "projects",
  projects: [],
  activeProjectId: null,
  dashboard: null,
  loading: false,
  error: "",
  message: "",
  newTopic: "",
  newNotes: "",
  newComments: "",
  newType: "phd",
  newDepartment: "pharma_chemistry",

  // Department configs
  departments: [
    { id: "pharma_chemistry", name: "Pharmaceutical Chemistry", desc: "Drug design, SAR, synthesis" },
    { id: "pharmacognosy", name: "Pharmacognosy", desc: "Natural products, phytochemicals" },
    { id: "pharmacology", name: "Pharmacology", desc: "Mechanism, PK/PD, toxicology" },
    { id: "pharmaceutics", name: "Pharmaceutics", desc: "Formulation, delivery, stability" },
    { id: "clinical_pharmacy", name: "Clinical Pharmacy", desc: "Clinical trials, outcomes" },
  ],

  // ── Deep Research state (merged from deep-research) ──
  drTopic: "",
  drMaxSources: 200,
  drYearFrom: "",
  drYearTo: "",
  drDatabases: ["pubmed", "semantic_scholar", "crossref", "openalex", "arxiv", "europe_pmc", "biorxiv"],
  drSessionId: "",
  drSources: [],
  drStats: null,
  drScanKeywords: "",
  drScannedSources: [],
  drSessions: [],

  get activeProject() {
    return this.projects.find(p => p.research_id === this.activeProjectId) || null;
  },
  get progressPct() {
    return Math.round((this.activeProject?.progress || 0) * 100);
  },

  async init() {
    await this.listProjects();
    await this.drLoadSessions();
  },

  async listProjects() {
    this.loading = true; this.error = "";
    try {
      const data = await callJsonApi("research/management/list");
      this.projects = Array.isArray(data) ? data : [];
      if (!this.projects.length) this.loading = false;
    } catch (e) { this.projects = []; }
    this.loading = false;
  },

  selectProject(id) {
    this.activeProjectId = id;
    this.loadDashboard();
  },

  async loadDashboard() {
    if (!this.activeProjectId) return;
    this.loading = true; this.error = "";
    try {
      const resp = await callJsonApi(`research/management/dashboard/${this.activeProjectId}`, {});
      this.dashboard = resp || null;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async startResearch() {
    if (!this.newTopic.trim()) return;
    this.loading = true; this.message = "";

    // 1. Open project creation modal
    if (typeof $store !== "undefined" && $store.projects) {
      try { $store.projects.openProjectsModal(); } catch {}
    }

    // 2. All 10 databases for comprehensive search
    const allDbs = "PubMed, Semantic Scholar, CrossRef, OpenAlex, Europe PMC, bioRxiv, arXiv, DrugBank, ChEMBL, KEGG";

    // 3. Send research prompt to agent with full-text-only instructions
    let prompt = `Research task: ${this.newTopic}\n`;
    prompt += `Type: ${this.newType}\n`;
    prompt += `Department: ${this.departments.find(d => d.id === this.newDepartment)?.name || this.newDepartment}\n`;
    if (this.newNotes.trim()) prompt += `Topics: ${this.newNotes}\n`;
    if (this.newComments.trim()) prompt += `Instructions: ${this.newComments}\n`;
    prompt += `\nPlease execute the following TWO-ROUND literature collection:\n\n`;
    prompt += `=== ROUND 1: Direct Full-Text Download ===\n`;
    prompt += `1. Search ALL 10 databases: ${allDbs}\n`;
    prompt += `2. For EVERY paper found, attempt to download the FULL-TEXT PDF immediately using:\n`;
    prompt += `   - Europe PMC full-text XML (open access)\n`;
    prompt += `   - Unpaywall API (legal open-access links)\n`;
    prompt += `   - Publisher direct PDF links\n`;
    prompt += `   - bioRxiv/arXiv direct PDF downloads\n`;
    prompt += `   - Any other合法 open-access source\n`;
    prompt += `3. Save ONLY papers where full text was successfully downloaded. Skip everything else.\n\n`;
    prompt += `=== ROUND 2: Hacker Agent Full-Text Retrieval ===\n`;
    prompt += `4. After Round 1, take ALL papers that FAILED to get full text in Round 1\n`;
    prompt += `5. Deploy the Hacker Agent to aggressively retrieve full text for each failed paper using:\n`;
    prompt += `   - Sci-Hub mirrors (try multiple domains)\n`;
    prompt += `   - LibGen / Library Genesis\n`;
    prompt += `   - Google Scholar PDF links\n`;
    prompt += `   - ResearchGate full-text requests\n`;
    prompt += `   - Author personal pages / institutional repositories\n`;
    prompt += `   - Wayback Machine / cached PDFs\n`;
    prompt += `   - Stealth browser scraping of publisher pages\n`;
    prompt += `   - Any other method to obtain the complete article\n`;
    prompt += `6. Save each newly retrieved full article to Knowledge Base\n\n`;
    prompt += `=== STORAGE RULES (STRICT) ===\n`;
    prompt += `7. Save each full article as BOTH formatted DOCX + original PDF in Knowledge Base with #${this.newType} tag\n`;
    prompt += `8. Synthesize ALL full-text articles into a comprehensive literature review\n`;
    prompt += `9. Track progress and provide updates after each round\n\n`;
    prompt += `\nCRITICAL RULES — READ CAREFULLY:\n`;
    prompt += `- NEVER save abstracts — they are useless for research\n`;
    prompt += `- NEVER save metadata-only (title, authors, DOI without full text)\n`;
    prompt += `- NEVER save summaries, snippets, or partial content\n`;
    prompt += `- ONLY save papers where you have the COMPLETE article body text\n`;
    prompt += `- If full text cannot be obtained after both rounds, DISCARD the paper — do not save it\n`;
    prompt += `- Every saved paper MUST have: Introduction, Methods, Results, Discussion, References — the full article\n`;

    const input = document.querySelector("#chat-input, #chat-bar-input textarea, .chat-bar-input textarea");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = "Research task sent to agent!";
    } else {
      this.message = "Type your research title in chat to start.";
    }

    this.newTopic = ""; this.newNotes = ""; this.newComments = "";
    this.loading = false;
    setTimeout(() => { this.message = ""; this.listProjects(); }, 5000);
  },

  exportReport() {
    const p = this.activeProject; if (!p) return;
    const d = this.dashboard || {};
    let md = `# ${p.topic || p.title}\nType: ${p.research_type} | Progress: ${this.progressPct}%\n\n`;
    (d.tasks || []).forEach(t => md += `- [${t.status}] ${t.title || t.id}\n`);
    const b = new Blob([md], { type: "text/plain" });
    const u = URL.createObjectURL(b); const a = document.createElement("a");
    a.href = u; a.download = "report.md"; a.click(); URL.revokeObjectURL(u);
  },

  // ═══════════════════════════════════════════════════════════════
  // Deep Research methods (merged from deep-research.html inline store)
  // ═══════════════════════════════════════════════════════════════

  drToggleDb(db) {
    const idx = this.drDatabases.indexOf(db);
    if (idx >= 0) this.drDatabases.splice(idx, 1);
    else this.drDatabases.push(db);
  },

  async drCollect() {
    if (!this.drTopic.trim()) { this.error = "Enter a research topic"; return; }
    this.loading = true; this.error = ""; this.message = ""; this.drSources = []; this.drStats = null;
    try {
      const r = await callJsonApi("deep_research", {
        action: "collect", topic: this.drTopic, max_sources: this.drMaxSources,
        databases: this.drDatabases, year_from: this.drYearFrom, year_to: this.drYearTo
      });
      if (r.status === "ok") {
        this.drSessionId = r.session_id;
        this.drSources = r.sources || [];
        this.drStats = r.stats || {};
        this.message = `${this.drStats.total} sources collected (${this.drStats.duplicates_removed} duplicates removed)`;
      } else { this.error = r.error || "Collection failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async drScan() {
    if (!this.drSessionId) { this.error = "Collect sources first"; return; }
    this.loading = true; this.error = "";
    const keywords = this.drScanKeywords.split(",").map(k => k.trim()).filter(Boolean);
    try {
      const r = await callJsonApi("deep_research", { action: "scan", session_id: this.drSessionId, keywords });
      if (r.status === "ok") {
        this.drScannedSources = r.top_sources || [];
        this.message = `${r.scanned} scanned, ${this.drScannedSources.length} top by relevance`;
        this.activeTab = "results";
      } else { this.error = r.error || "Scan failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async drStoreToKB() {
    if (!this.drSessionId) { this.error = "Collect sources first"; return; }
    this.loading = true; this.error = "";
    try {
      const r = await callJsonApi("deep_research", { action: "store", session_id: this.drSessionId, max_store: 50, topic: this.drTopic });
      if (r.status === "ok") {
        this.message = `${r.stored} papers stored in Knowledge Base`;
      } else { this.error = r.error || "Store failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async drLoadSessions() {
    try {
      const r = await callJsonApi("deep_research", { action: "list" });
      if (r.status === "ok") this.drSessions = r.sessions || [];
    } catch (e) {}
  },

  drFormatYear(y) { return y ? String(y) : "N/A"; },
});
