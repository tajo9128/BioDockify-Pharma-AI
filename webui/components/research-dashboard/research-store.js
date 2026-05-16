import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

async function safeGet(path) {
  try { const r = await fetchApi(path, { method: "GET" }); const t = await r.text(); return JSON.parse(t); }
  catch { return []; }
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
  newNotes: "",
  newComments: "",
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
    try { const data = await safeGet("research/management/list"); this.projects = Array.isArray(data) ? data : []; }
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
    try { const data = await safeGet("research/management/dashboard/" + this.activeProjectId); this.dashboard = data || null; }
    catch (e) { this.error = e.message; this.dashboard = null; }
    this.loading = false;
  },

  startResearch() {
    if (!this.newTopic.trim()) return;

    // Build comprehensive research prompt for agent
    let prompt = `START RESEARCH PIPELINE\n\nTitle: ${this.newTopic}\nType: ${this.newType}\n`;
    if (this.newNotes.trim()) prompt += `Topics/Objectives:\n${this.newNotes}\n`;
    if (this.newComments.trim()) prompt += `Additional Comments:\n${this.newComments}\n`;
    prompt += `\nExecute the complete research workflow:\n`;
    prompt += `1. Deep Research: Search literature across PubMed, Semantic Scholar, arXiv\n`;
    prompt += `2. Literature Review: Synthesize findings, identify gaps\n`;
    prompt += `3. Knowledge Extraction: Save key papers and findings to Knowledge Base\n`;
    prompt += `4. Hypothesis Generation: Form research hypotheses from gaps\n`;
    prompt += `5. Progress Tracking: Create milestones and track progress\n`;
    prompt += `6. Academic Writing: Generate literature review draft\n\n`;
    prompt += `Also call the API: POST /api/research/management/comprehensive/initialize with {topic:"${this.newTopic}", research_type:"${this.newType}", user_message:"Research on ${this.newTopic}"}\n`;
    prompt += `Monitor progress via GET /api/research/management/list`;

    const input = document.querySelector("#chat-bar-input textarea, .chat-bar-input textarea, .input-area textarea");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = "Research pipeline sent to agent. Agent will execute deep research, literature review, and tracking.";
      this.newTopic = "";
      this.newNotes = "";
      this.newComments = "";
      setTimeout(() => { this.message = ""; this.listProjects(); }, 5000);
    } else {
      this.error = "Chat input not found. Please open a chat first.";
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
