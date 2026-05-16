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
    this.loading = true; this.error = ""; this.message = "";
    try {
      // Try API first
      const resp = await callJsonApi("research/management/comprehensive/initialize", {
        topic: this.newTopic, research_type: this.newType,
        user_message: [this.newTopic, this.newNotes, this.newComments].filter(Boolean).join("\n"),
      });
      if (resp.research_id) {
        this.message = "Pipeline started: " + resp.research_id;
        this.activeProjectId = resp.research_id;
        this.newTopic = ""; this.newNotes = ""; this.newComments = "";
        await this.listProjects();
        this.loadDashboard();
        this.loading = false;
        return;
      }
    } catch (e) { /* API unavailable, use agent fallback */ }

    // Fallback: send to agent chat
    this.loading = false;
    let prompt = `START RESEARCH PIPELINE\nTitle: ${this.newTopic}\nType: ${this.newType}\n`;
    if (this.newNotes.trim()) prompt += `Topics/Objectives:\n${this.newNotes}\n`;
    if (this.newComments.trim()) prompt += `Comments:\n${this.newComments}\n`;
    prompt += `Execute: 1) Deep Research via literature APIs, 2) Literature Review synthesis, 3) Save findings to Knowledge Base.`;
    const input = document.querySelector("#chat-input, #chat-bar-input textarea, .chat-bar-input textarea");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = "Pipeline sent to agent. Agent will execute deep research and literature review.";
      this.newTopic = ""; this.newNotes = ""; this.newComments = "";
      setTimeout(() => { this.message = ""; this.listProjects(); }, 5000);
    } else {
      this.error = "Chat input not found. Type your research title in chat to start.";
    }
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
