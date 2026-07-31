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
      const data = await callJsonApi("research_management", { action: "list" });
      this.projects = Array.isArray(data?.projects) ? data.projects : (Array.isArray(data) ? data : []);
    } catch (e) { this.projects = []; this.error = e.message || "Failed to load projects"; }
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
      const resp = await callJsonApi("research_management", {
        action: "dashboard",
        research_id: this.activeProjectId,
      });
      if (resp.error) { this.error = resp.error; this.dashboard = null; }
      else this.dashboard = resp || null;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async startResearch() {
    if (!this.newTopic.trim()) return;
    this.loading = true; this.message = ""; this.error = "";

    const topic = this.newTopic.trim();
    const researchType = this.newType;
    const department = this.newDepartment;
    const notes = this.newNotes.trim();
    const comments = this.newComments.trim();

    // 1. Persist project via Flask research_management (was unmounted FastAPI)
    let researchId = null;
    try {
      const created = await callJsonApi("research_management", {
        action: "create",
        topic,
        research_type: researchType,
        department,
        notes: [notes, comments].filter(Boolean).join(" | "),
      });
      if (created.error) {
        this.error = created.error;
        this.loading = false;
        return;
      }
      researchId = created.research_id;
      this.activeProjectId = researchId;
      await this.listProjects();
    } catch (e) {
      this.error = "Failed to save project: " + (e.message || e);
      this.loading = false;
      return;
    }

    // 2. Optional: nudge agent chat with a literature-collection brief
    const allDbs = "PubMed, Semantic Scholar, CrossRef, OpenAlex, Europe PMC, bioRxiv, arXiv";
    let prompt = `Research task: ${topic}\n`;
    prompt += `Project ID: ${researchId}\n`;
    prompt += `Type: ${researchType}\n`;
    prompt += `Department: ${this.departments.find(d => d.id === department)?.name || department}\n`;
    if (notes) prompt += `Topics: ${notes}\n`;
    if (comments) prompt += `Instructions: ${comments}\n`;
    prompt += `\nCollect FULL-TEXT open-access papers only from: ${allDbs}.\n`;
    prompt += `Use Europe PMC / Unpaywall / publisher OA / preprint PDFs. Do not store abstracts-only.\n`;
    prompt += `Store complete articles in Knowledge Base tagged #${researchType}.\n`;

    const input = document.querySelector("#chat-input, #chat-bar-input textarea, .chat-bar-input textarea");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = `Project saved (${researchId}). Research brief sent to agent.`;
    } else {
      this.message = `Project saved (${researchId}). Open chat to continue with the agent.`;
    }

    this.newTopic = ""; this.newNotes = ""; this.newComments = "";
    this.activeTab = "pipeline";
    await this.loadDashboard();
    this.loading = false;
    setTimeout(() => { this.message = ""; }, 6000);
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
