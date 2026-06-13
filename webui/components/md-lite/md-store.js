import { callJsonApi } from "/js/api.js";

Alpine.data("mdLite", () => ({
  step: 1, jobId: null, loading: false, errorMessage: "", result: null,
  status: null, _pollTimer: null,

  // Settings
  inputMethod: "complex",  // complex | separate | docking
  settings: { total_ns: 5, platform: "CUDA", forcefield: "amber14", temperature: 300, pressure: 1.0 },
  dockingJob: "",

  init() {
    this.checkHealth();
  },

  async checkHealth() {
    try {
      const r = await callJsonApi("md_lite", { action: "health" });
      this.health = r;
      if (r.gpu) this.settings.platform = "CUDA";
      else if (r.platforms?.some(p => p.name.includes("OpenCL"))) this.settings.platform = "OpenCL";
      else this.settings.platform = "CPU";
    } catch {}
  },

  // Step 1: File upload
  pickFile(target) {
    const i = document.createElement("input");
    i.type = "file"; i.accept = ".pdb,.pdbqt,.sdf,.mol2,.gro";
    i.onchange = (e) => {
      const f = e.target.files?.[0]; i.remove();
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => { this[target] = reader.result; this["_"+target+"Name"] = f.name; };
      reader.readAsText(f);
    };
    document.body.appendChild(i); i.click();
  },

  // Step 2: Prepare system
  async prepare() {
    this.loading = true; this.errorMessage = ""; this.jobId = null;
    try {
      const payload = { action: "prepare", forcefield: this.settings.forcefield, temperature: this.settings.temperature, platform: this.settings.platform };
      if (this.inputMethod === "complex" && this._complexContent) {
        payload.complex_pdb = this._complexContent;
      } else if (this.inputMethod === "separate") {
        payload.protein_pdb = this._proteinContent;
        payload.ligand_sdf = this._ligandContent;
      } else if (this.inputMethod === "docking") {
        const r = await callJsonApi("md_lite", { action: "import_docking", docking_job_id: this.dockingJob });
        if (r.status === "ok") this.jobId = r.job_id;
        this.loading = false; return;
      }
      const r = await callJsonApi("md_lite", payload);
      if (r.status === "ok") { this.jobId = r.job_id; this.step = 2; }
      else { this.errorMessage = r.error || "Prepare failed"; }
    } catch (e) { this.errorMessage = "Prepare error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  // Step 3: Run MD
  async runMD() {
    this.loading = true; this.errorMessage = "";
    try {
      const r = await callJsonApi("md_lite", {
        action: "run", job_id: this.jobId,
        total_ns: this.settings.total_ns, forcefield: this.settings.forcefield,
        temperature: this.settings.temperature, pressure: this.settings.pressure,
        platform: this.settings.platform,
      });
      if (r.status === "ok") { this.step = 3; this.startPolling(); }
      else { this.errorMessage = r.error || "Run failed"; }
    } catch (e) { this.errorMessage = "Run error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  startPolling() {
    this.pollStatus();
    this._pollTimer = setInterval(() => this.pollStatus(), 3000);
  },

  async pollStatus() {
    if (!this.jobId) return;
    try {
      const r = await callJsonApi("md_lite", { action: "status", job_id: this.jobId });
      this.status = r;
      if (r.status === "completed" || r.status === "error" || r.status === "stopped") {
        clearInterval(this._pollTimer);
        if (r.status === "completed") this.loadResults();
      }
    } catch {}
  },

  async loadResults() {
    try {
      const r = await callJsonApi("md_lite", { action: "results", job_id: this.jobId });
      this.result = r.analysis || r;
    } catch {}
  },

  async stopMD() {
    try {
      await callJsonApi("md_lite", { action: "stop", job_id: this.jobId });
      clearInterval(this._pollTimer);
      this.status = { status: "stopped" };
    } catch {}
  },

  async download() {
    if (!this.jobId) return;
    window.open("/api/md_lite?action=download&job_id=" + this.jobId, "_blank");
  },

  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry("MD Lite — " + this.jobId, JSON.stringify(this.result, null, 2), "MD Simulation", ["md_lite", "simulation"]);
    }
  },

  resetAll() {
    clearInterval(this._pollTimer);
    this.step = 1; this.jobId = null; this.result = null; this.status = null;
    this.errorMessage = "";
    this._complexContent = null; this._proteinContent = null; this._ligandContent = null;
    this._complexContentName = ""; this._proteinContentName = ""; this._ligandContentName = "";
  },
}));
