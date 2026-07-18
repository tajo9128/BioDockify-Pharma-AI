import { callJsonApi } from "/js/api.js";

Alpine.data("mdLite", () => ({
  step: 1, jobId: null, loading: false, errorMessage: "", result: null,
  status: null, _pollTimer: null,

  // Input
  inputMethod: "complex",
  _complexContent: null, _proteinContent: null, _ligandContent: null,
  _complexName: "", _proteinName: "", _ligandName: "",
  dockingJob: "", jobList: [],
  dragging: false,

  // Settings
  settings: { total_ns: 5, platform: "CUDA", forcefield: "amber14", temperature: 300, pressure: 1.0 },
  expandedAdvanced: false,
  gpuAvailable: false,
  gpuName: "",

  // Live monitor
  liveLog: [],
  mmpbsaLoading: false, mmpbsaResult: null,

  init() {
    this.checkHealth();
  },

  async checkHealth() {
    try {
      const r = await callJsonApi("md_lite", { action: "health" });
      const platforms = r.platforms || [];
      if (platforms.some(p => p.name.includes("CUDA"))) {
        this.settings.platform = "CUDA"; this.gpuAvailable = true;
        const c = platforms.find(p => p.name.includes("CUDA"));
        this.gpuName = c ? c.name : "CUDA";
      } else if (platforms.some(p => p.name.includes("OpenCL"))) {
        this.settings.platform = "OpenCL"; this.gpuAvailable = true;
      } else {
        this.settings.platform = "CPU"; this.gpuAvailable = false;
      }
    } catch {}
  },

  // File upload
  pickFile(key) {
    const i = document.createElement("input"); i.type = "file";
    i.accept = ".pdb,.pdbqt,.sdf,.mol2,.gro";
    i.onchange = (e) => {
      const f = e.target.files?.[0]; i.remove(); if (!f) return;
      const r = new FileReader();
      r.onload = () => { this["_"+key+"Content"] = r.result; this["_"+key+"Name"] = f.name; };
      r.readAsText(f);
    };
    document.body.appendChild(i); i.click();
  },

  // Prepare system (standard)
  async prepare() {
    this.loading = true; this.errorMessage = ""; this.jobId = null; this.liveLog = [];
    try {
      const p = { action: "prepare", forcefield: this.settings.forcefield, temperature: this.settings.temperature, platform: this.settings.platform };
      if (this.inputMethod === "complex" && this._complexContent) {
        p.complex_pdb = this._complexContent;
      } else if (this.inputMethod === "separate" && this._proteinContent) {
        p.protein_pdb = this._proteinContent;
        if (this._ligandContent) p.ligand_sdf = this._ligandContent;
      } else if (this.inputMethod === "docking" && this.dockingJob) {
        const r = await callJsonApi("md_lite", { action: "import_docking", docking_job_id: this.dockingJob });
        this.loading = false; return;
      }
      const r = await callJsonApi("md_lite", p);
      if (r.status === "ok") { this.jobId = r.job_id; this.step = 2; this.liveLog.push(`Minimization complete · ${r.min_energy_kjmol} kJ/mol`); }
      else { this.errorMessage = r.error || "Prepare failed"; }
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  // Auto-prepare complex (PDBFixer + RDKit) — bridges docking → MD
  async prepareComplex() {
    this.loading = true; this.errorMessage = ""; this.jobId = null; this.liveLog = [];
    try {
      const p = { action: "prepare_complex" };
      if (this._proteinContent) p.protein_pdb_path = this._proteinName;
      if (this._ligandContent) p.ligand_pdbqt_path = this._ligandName;
      // Pass file content for server-side processing
      if (this._proteinContent) {
        p.protein_pdb_content = this._proteinContent;
        p.ligand_pdbqt_content = this._ligandContent || "";
      }
      const r = await callJsonApi("md_lite", p);
      if (r.status === "ok") {
        this.jobId = r.job_id;
        this.step = 2;
        this.liveLog.push(`Complex prepared: ${r.total_atoms} atoms (${r.protein_atoms} protein + ${r.ligand_atoms} ligand)`);
        if (r.ligand_smiles) this.liveLog.push(`Ligand SMILES: ${r.ligand_smiles}`);
        this.liveLog.push(r.message || "Ready for MD simulation");
      } else {
        this.errorMessage = r.error || "Complex preparation failed";
      }
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  // Run MD
  async runMD() {
    this.loading = true; this.errorMessage = ""; this.liveLog = [];
    try {
      const r = await callJsonApi("md_lite", {
        action: "run", job_id: this.jobId, total_ns: this.settings.total_ns,
        forcefield: this.settings.forcefield, temperature: this.settings.temperature,
        pressure: this.settings.pressure, platform: this.settings.platform,
      });
      if (r.status === "ok") { this.step = 3; this.startPolling(); }
      else { this.errorMessage = r.error || "Run failed"; }
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  startPolling() {
    this.liveLog.push("Production MD started");
    this._lastProgress = 0;
    this._lastTime = Date.now();
    this.pollStatus();
    this._pollTimer = setInterval(() => this.pollStatus(), 3000);
  },

  async pollStatus() {
    if (!this.jobId) return;
    try {
      const r = await callJsonApi("md_lite", { action: "status", job_id: this.jobId });
      this.status = r;
      // Add chunks to live log when progress changes
      if (r.chunk && r.progress_pct !== this._lastProgress) {
        this._lastProgress = r.progress_pct;
        this.liveLog.push(`Segment ${r.chunk} · ${r.progress_ns} ns · ${r.progress_pct}%`);
        if (this.liveLog.length > 20) this.liveLog.shift();
      }
      if (r.status === "completed" || r.status === "error" || r.status === "stopped") {
        clearInterval(this._pollTimer);
        this.liveLog.push(r.status === "completed" ? "Simulation complete ✓" : "Simulation " + r.status);
        if (r.status === "completed") this.loadResults();
      }
    } catch {}
  },

  async loadResults() {
    try {
      const r = await callJsonApi("md_lite", { action: "results", job_id: this.jobId });
      this.result = r.analysis || r;
      // Build metrics table
      this.result._metrics = [];
      if (this.result.rmsd) this.result._metrics.push({label:"RMSD", value:this.result.rmsd.final_nm+" nm", color:"#00d4aa"});
      if (this.result.rmsf) this.result._metrics.push({label:"RMSF", value:this.result.rmsf.max_nm+" nm", color:"#6366f1"});
      if (this.result.energy) this.result._metrics.push({label:"Energy", value:this.result.energy.mean+" kJ", color:"#f59e0b"});
      if (this.result.gyration) this.result._metrics.push({label:"Rg", value:this.result.gyration.final_nm+" nm", color:"#8b5cf6"});
      if (this.result.sasa) this.result._metrics.push({label:"SASA", value:this.result.sasa.final_nm2+" nm²", color:"#22c55e"});
      if (this.result.hbonds) this.result._metrics.push({label:"H-Bonds", value:this.result.hbonds.avg_per_frame||0, color:"#f59e0b"});
    } catch {}
  },

  async stopMD() {
    try { await callJsonApi("md_lite", { action: "stop", job_id: this.jobId }); clearInterval(this._pollTimer); }
    catch {}
  },

  download() { if (this.jobId) window.open("/api/md_lite?action=download&job_id="+this.jobId, "_blank"); },

  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry("MD Lite — " + this.jobId, JSON.stringify(this.result,null,2), "MD Simulation", ["md_lite","simulation"]);
    }
  },

  async runMMPBSA() {
    this.mmpbsaLoading = true; this.mmpbsaResult = null; this.errorMessage = "";
    try {
      const r = await callJsonApi("md_lite", { action: "mmpbsa", job_id: this.jobId });
      if (r.status === "ok" && r.mmpbsa) this.mmpbsaResult = r.mmpbsa;
      else this.errorMessage = r.mmpbsa?.error || r.error || "MM-PBSA failed";
    } catch (e) { this.errorMessage = "MM-PBSA: " + (e.message || "API unavailable"); }
    this.mmpbsaLoading = false;
  },

  resetAll() {
    clearInterval(this._pollTimer); this.step = 1; this.jobId = null;
    this.result = null; this.status = null; this.errorMessage = ""; this.liveLog = [];
    this.mmpbsaResult = null; this.mmpbsaLoading = false;
    this._complexContent = null; this._proteinContent = null; this._ligandContent = null;
    this._complexName = ""; this._proteinName = ""; this._ligandName = "";
  },
}));
