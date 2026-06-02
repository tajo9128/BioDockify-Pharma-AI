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

  get activeProject() {
    return this.projects.find(p => p.research_id === this.activeProjectId) || null;
  },
  get progressPct() {
    return Math.round((this.activeProject?.progress || 0) * 100);
  },

  async init() {
    await this.listProjects();
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

    // 2. Get department-specific databases
    const deptDbs = {
      pharma_chemistry: "PubMed, SciFinder, Reaxys, ChEMBL, DrugBank",
      pharmacognosy: "PubMed, NAPRALERT, KNapsack, ChemSpider, PubChem",
      pharmacology: "PubMed, DrugBank, ChEMBL, KEGG, Reactome",
      pharmaceutics: "PubMed, FDA Orange Book, Excipient DB",
      clinical_pharmacy: "PubMed, ClinicalTrials.gov, Cochrane, Embase",
    };
    const dbs = deptDbs[this.newDepartment] || "PubMed, Semantic Scholar, Google Scholar";

    // 3. Send research prompt to agent
    let prompt = `Research task: ${this.newTopic}\n`;
    prompt += `Type: ${this.newType}\n`;
    prompt += `Department: ${this.departments.find(d => d.id === this.newDepartment)?.name || this.newDepartment}\n`;
    if (this.newNotes.trim()) prompt += `Topics: ${this.newNotes}\n`;
    if (this.newComments.trim()) prompt += `Instructions: ${this.newComments}\n`;
    prompt += `\nPlease:\n`;
    prompt += `1. Search databases: ${dbs}\n`;
    prompt += `2. Synthesize findings into a literature review\n`;
    prompt += `3. Save papers to Knowledge Base with #${this.newType} tag\n`;
    prompt += `4. Track progress and provide updates\n`;

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
});
