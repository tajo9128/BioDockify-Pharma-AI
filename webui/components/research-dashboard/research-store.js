import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, fetchApi } from "/js/api.js";

async function apiGet(path) {
  const r = await fetchApi(path, { method: "GET" });
  return r.json();
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
    try { this.projects = await apiGet("research/management/list") || []; }
    catch (e) { this.error = e.message; this.projects = []; }
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
      const resp = await apiGet("research/management/dashboard/" + this.activeProjectId);
      this.dashboard = resp || null;
    } catch (e) { this.error = e.message; this.dashboard = null; }
    this.loading = false;
  },

  async startResearch() {
    if (!this.newTopic.trim()) return;
    this.loading = true; this.error = ""; this.message = "";
    try {
      const resp = await callJsonApi("research/management/comprehensive/initialize", {
        topic: this.newTopic, research_type: this.newType, user_message: this.newTopic,
      });
      if (resp.research_id) {
        this.message = "Pipeline started: " + resp.research_id;
        this.activeProjectId = resp.research_id;
        this.newTopic = "";
        await this.listProjects();
        this.loadDashboard();
      } else { this.error = resp.error || "Failed to start"; }
    } catch (e) { this.error = e.message; }
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
