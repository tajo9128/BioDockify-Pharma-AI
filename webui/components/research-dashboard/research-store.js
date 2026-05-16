import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

async function safeGet(path) {
  try {
    const r = await fetchApi(path, { method: "GET" });
    const txt = await r.text();
    return JSON.parse(txt);
  } catch { return []; }
}

export const store = createStore("researchDashboard", {
  activeTab: "projects",
  projects: [],
  activeProjectId: null,
  dashboard: null,
  loading: false,
  error: "",
  message: "",
  newTopic: "",
  newType: "phd",

  get activeProject() {
    return this.projects.find(p => p.research_id === this.activeProjectId) || null;
  },
  get progressPct() {
    return Math.round((this.activeProject?.progress || 0) * 100);
  },

  async init() { await this.listProjects(); },

  async listProjects() {
    this.loading = true; this.error = "";
    try {
      const data = await safeGet("research/management/list");
      this.projects = Array.isArray(data) ? data : [];
    } catch (e) { this.error = e.message; this.projects = []; }
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
      const data = await safeGet("research/management/dashboard/" + this.activeProjectId);
      this.dashboard = data || null;
    } catch (e) { this.error = e.message; this.dashboard = null; }
    this.loading = false;
  },

  async startResearch() {
    if (!this.newTopic.trim()) return;
    this.loading = true; this.error = ""; this.message = "";
    try {
      const r = await fetchApi("research/management/comprehensive/initialize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: this.newTopic, research_type: this.newType, user_message: this.newTopic }),
      });
      const txt = await r.text();
      try {
        const resp = JSON.parse(txt);
        if (resp.research_id) {
          this.message = "Pipeline started: " + resp.research_id;
          this.activeProjectId = resp.research_id;
          this.newTopic = "";
          await this.listProjects();
          this.loadDashboard();
        } else { this.error = resp.error || "Failed to start"; }
      } catch { this.error = "Server returned invalid response. The research pipeline may not be configured."; }
    } catch (e) { this.error = "Cannot reach research API. Starting research requires the backend service."; }
    this.loading = false;
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
