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
      const data = await safeGet("research/management/list");
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

    // 2. Send research prompt to agent
    let prompt = `CREATE RESEARCH PROJECT & START PIPELINE\n\nProject Title: ${this.newTopic}\nType: ${this.newType}\n`;
    if (this.newNotes.trim()) prompt += `Topics:\n${this.newNotes}\n`;
    if (this.newComments.trim()) prompt += `Instructions:\n${this.newComments}\n`;
    prompt += `\nExecute complete research workflow:\n`;
    prompt += `1. Create a new project named "${this.newTopic}" via projects system\n`;
    prompt += `2. Deep Research: search PubMed, Semantic Scholar, arXiv\n`;
    prompt += `3. Literature Review: synthesize findings, identify gaps\n`;
    prompt += `4. Save all papers to Knowledge Base with #${this.newType} tag\n`;
    prompt += `5. Track progress and provide regular updates\n`;

    const input = document.querySelector("#chat-input, #chat-bar-input textarea, .chat-bar-input textarea");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = "Project creation + research pipeline sent to agent!";
    } else {
      this.message = "Project modal opened. Type your research title in chat to start.";
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
