import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, fetchApi } from "/js/api.js";

async function apiGet(path) {
  const resp = await fetchApi(path, { method: "GET" });
  return resp.json();
}

export const store = createStore("researchDashboard", {
  activeTab: "projects",
  projects: [],
  activeProjectId: null,
  loading: false,
  error: "",
  message: "",

  // Pipeline
  dashboard: null,
  stages: [],
  tasks: [],

  // Milestones
  milestones: [],
  thesisReport: null,

  // Wet Lab
  wetlabSummary: null,
  wetlabExperiments: [],

  // New project form
  newTopic: "",
  newType: "phd",

  get activeProject() {
    return this.projects.find(p => p.research_id === this.activeProjectId) || null;
  },

  get progressPct() {
    return Math.round((this.activeProject?.progress || 0) * 100);
  },

  get stageNames() {
    return ["detected","planning","todo_generated","deep_research","web_scraping","analysis","storage","completed","failed"];
  },

  switchTab(tab) {
    this.activeTab = tab;
    if (tab !== "projects" && this.activeProjectId) {
      if (tab === "pipeline" || tab === "milestones" || tab === "wetlab") {
        this.loadDashboard();
      }
    }
  },

  async listProjects() {
    this.loading = true;
    this.error = "";
    try {
      const resp = await apiGet("research/management/list");
      this.projects = resp || [];
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  selectProject(id) {
    this.activeProjectId = id;
    this.loadDashboard();
  },

  async loadDashboard() {
    if (!this.activeProjectId) return;
    this.loading = true;
    this.error = "";
    try {
      const resp = await apiGet("research/management/dashboard/" + this.activeProjectId);
      this.dashboard = resp;
      this.stages = resp.pipeline?.stages || resp.stages || [];
      this.tasks = resp.pipeline?.tasks || resp.tasks || [];
      this.milestones = resp.thesis?.milestones || resp.milestones || [];
      this.thesisReport = resp.thesis || null;
      this.wetlabSummary = resp.wetlab?.summary || resp.wetlab_summary || null;
      this.wetlabExperiments = resp.wetlab?.experiments || resp.wetlab_experiments || [];
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async initComprehensive() {
    if (!this.newTopic.trim()) return;
    this.loading = true;
    this.error = "";
    this.message = "";
    try {
      const resp = await callJsonApi("research/management/comprehensive/initialize", {
        topic: this.newTopic,
        research_type: this.newType,
        user_message: this.newTopic,
      });
      if (resp.research_id) {
        this.message = "Research pipeline started: " + resp.research_id;
        this.activeProjectId = resp.research_id;
        this.newTopic = "";
        await this.listProjects();
        this.loadDashboard();
      } else if (resp.error) {
        this.error = resp.error;
      }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async updateTaskStatus(researchId, taskId, status) {
    try {
      await fetch("/api/research/management/task/" + researchId + "/" + taskId, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": await getCsrfToken() },
        body: JSON.stringify({ status }),
      });
      this.loadDashboard();
    } catch (e) { this.error = e.message; }
  },

  async wetlabStart(experimentId) {
    try {
      await callJsonApi("research/management/wetlab/start/" + experimentId);
      this.loadDashboard();
    } catch (e) { this.error = e.message; }
  },

  async wetlabSubmit(experimentId, data) {
    try {
      await callJsonApi("research/management/wetlab/submit", {
        experiment_id: experimentId,
        results: data,
      });
      this.loadDashboard();
    } catch (e) { this.error = e.message; }
  },

  async updateMilestone(researchId, milestoneId, status, progress) {
    try {
      await callJsonApi("research/management/thesis/milestone", {
        research_id: researchId,
        milestone_id: milestoneId,
        status,
        progress,
      });
      this.loadDashboard();
    } catch (e) { this.error = e.message; }
  },

  async deleteProject(researchId) {
    if (!confirm("Delete this research project? This cannot be undone.")) return;
    try {
      await callJsonApi("research/management/task/" + researchId + "/cancel");
    } catch {}
    await this.listProjects();
    this.activeProjectId = null;
    this.dashboard = null;
  },

  exportReport() {
    if (!this.activeProject) return;
    const r = this.activeProject;
    const report = [
      `# Research Report: ${r.topic || r.title || "Untitled"}`,
      `Type: ${r.research_type || "N/A"} | Stage: ${r.current_stage || "N/A"} | Progress: ${Math.round((r.progress || 0) * 100)}%`,
      ``,
      `## Pipeline Stages`,
    ];
    this.stages.forEach(s => {
      report.push(`- ${s.title || s.stage || s}: ${s.status || "pending"}`);
    });
    if (this.tasks.length) {
      report.push(``, `## Tasks`);
      this.tasks.forEach(t => {
        report.push(`- [${t.status || "pending"}] ${t.title || t.description || t.id}`);
      });
    }
    if (this.milestones.length) {
      report.push(``, `## Milestones`);
      this.milestones.forEach(m => {
        report.push(`- ${m.status || "pending"} (${Math.round((m.progress || 0) * 100)}%) ${m.title || ""} — Deadline: ${(m.deadline || "").substring(0, 10)}`);
      });
    }
    if (this.wetlabSummary) {
      report.push(``, `## Wet Lab: ${this.wetlabSummary.total || 0} experiments (${this.wetlabSummary.completed || 0} completed, ${this.wetlabSummary.running || 0} running)`);
    }
    report.push(``, `---`, `Generated: ${new Date().toISOString()}`);

    const blob = new Blob([report.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research-report-${(r.topic || "report").replace(/\s+/g, "-").substring(0, 40)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  },

  openInAcademicWriter() {
    if (!this.activeProject) return;
    const topic = this.activeProject.topic || this.activeProject.title || "";
    if (typeof $store !== "undefined" && $store.desktopWorkspace) {
      $store.desktopWorkspace.openWindow("thesis");
    }
    setTimeout(() => {
      const input = document.querySelector(".aw-topic-input");
      if (input) {
        input.value = topic;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }, 300);
  },

  stageStatusClass(stage) {
    const current = this.activeProject?.current_stage || "";
    const idx = this.stageNames.indexOf(stage);
    const curIdx = this.stageNames.indexOf(current);
    if (idx < curIdx) return "done";
    if (idx === curIdx) return "active";
    return "pending";
  },

  milestoneColor(status) {
    return {
      completed: "#22c55e", in_progress: "#4fc3f7", not_started: "#555",
      delayed: "#ffd93d", on_hold: "#ff6b6b", cancelled: "#888",
    }[status] || "#555";
  },
});

async function getCsrfToken() {
  try { const r = await fetch("/api/csrf_token"); const j = await r.json(); return j.token; }
  catch { return ""; }
}
