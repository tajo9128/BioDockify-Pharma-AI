import { fetchApi } from "/js/api.js";

async function apiGet(path) {
  const resp = await fetchApi(path, { method: "GET" });
  const txt = await resp.text();
  try { return JSON.parse(txt); } catch { return []; }
}

export const store = Alpine.reactive({
  activeTab: "projects",
  projects: [],
  activeProjectId: null,
  dashboard: null,
  loading: false,
  error: "",
  message: "",
  newTopic: "",
  newType: "phd",

  async init() {
    await this.listProjects();
  },

  async listProjects() {
    this.loading = true; this.error = "";
    try { this.projects = await apiGet("research/management/list") || []; }
    catch (e) { this.error = e.message; }
    this.loading = false;
  },

  selectProject(id) {
    this.activeProjectId = id;
    this.loadDashboard();
  },

  async loadDashboard() {
    if (!this.activeProjectId) return;
    this.loading = true; this.error = "";
    try { this.dashboard = await apiGet("research/management/dashboard/" + this.activeProjectId); }
    catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async startResearch() {
    if (!this.newTopic.trim()) return;
    this.loading = true; this.error = ""; this.message = "";
    try {
      const resp = await fetchApi("research/management/comprehensive/initialize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: this.newTopic, research_type: this.newType, user_message: this.newTopic }),
      });
      const data = await resp.json();
      if (data.research_id) {
        this.message = "Started: " + data.research_id;
        this.activeProjectId = data.research_id;
        this.newTopic = "";
        await this.listProjects();
      } else if (data.error) { this.error = data.error; }
      else { this.error = "Failed to start research"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  get activeProject() {
    return this.projects.find(p => p.research_id === this.activeProjectId) || null;
  },

  get progressPct() { return Math.round((this.activeProject?.progress || 0) * 100); },

  exportReport() {
    const p = this.activeProject; if (!p) return;
    const d = this.dashboard || {};
    let md = `# Research: ${p.topic || p.title}\nType: ${p.research_type || "N/A"} | Progress: ${this.progressPct}%\n\n`;
    (d.tasks || []).forEach(t => { md += `- [${t.status}] ${t.title || t.id}\n`; });
    (d.milestones || []).forEach(m => { md += `- ${m.status} ${Math.round((m.progress||0)*100)}% ${m.title}\n`; });
    const b = new Blob([md], { type: "text/plain" });
    const u = URL.createObjectURL(b); const a = document.createElement("a");
    a.href = u; a.download = "research-report.md"; a.click(); URL.revokeObjectURL(u);
  },
});

Alpine.store("researchDashboard", Alpine.raw(store));
