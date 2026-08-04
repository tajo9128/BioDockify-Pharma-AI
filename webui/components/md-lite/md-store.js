import { callJsonApi } from "/js/api.js";

const mdLiteFactory = () => ({
  step: 1, jobId: null, loading: false, errorMessage: "", result: null,
  status: null, _pollTimer: null, _logPollTimer: null,

  // Input
  inputMethod: "complex",
  _complexContent: null, _proteinContent: null, _ligandContent: null,
  _complexName: "", _proteinName: "", _ligandName: "",
  dockingJob: "", jobList: [],
  dragging: false,

  // Settings — fast defaults: 1ns, auto platform
  settings: { total_ns: 1, platform: "auto", forcefield: "amber14", temperature: 300, pressure: 1.0, fast_mode: true },
  expandedAdvanced: false,
  gpuAvailable: false,
  gpuName: "",
  platformWarning: "",

  // Live monitor
  liveLog: [],
  mdLog: [],
  expandedLog: false,
  _lastPhase: null,
  mmpbsaLoading: false, mmpbsaResult: null,
  advancedLoading: false, advancedResult: null,
  showAdvanced: false,

  // Phase display
  phaseLabels: {
    idle: "Idle", preparing: "Preparing PDB", preparing_complex: "Preparing complex",
    sanitizing: "Sanitizing PDB", parameterizing: "Parameterizing",
    solvating: "Adding solvent", minimizing: "Minimizing energy",
    equilibrating: "Equilibrating", starting: "Starting MD",
    running: "Running MD", completed: "Complete ✓", stopped: "Stopped",
    interrupted: "Interrupted (sleep/crash) — Resume available",
    resuming: "Resuming from checkpoint...",
    error: "Error", unknown: "Unknown"
  },

  get phaseLabel() {
    const p = this.status?.phase || "idle";
    return this.phaseLabels[p] || p;
  },

  get phaseColor() {
    const p = this.status?.phase || "idle";
    if (p === "error") return "#ef4444";
    if (p === "completed") return "#22c55e";
    if (p === "stopped") return "#f59e0b";
    if (p === "running") return "#6366f1";
    return "#94a3b8";
  },

  init() {
    this.checkHealth();
  },

  async checkHealth() {
    try {
      const r = await callJsonApi("md_lite", { action: "health" });
      this.platformWarning = "";
      if (r.status === "error" || r.error) {
        this.platformWarning = "OpenMM not available: " + (r.error || "install failed") + ". MD Lite will not work until OpenMM is installed.";
        return;
      }
      // Support both old (r.gpu) and new (r.gpu_available) response shapes
      const hasGpu = r.gpu_available ?? r.gpu ?? false;
      const usingGpu = r.using_gpu ?? hasGpu;
      if (hasGpu) {
        this.gpuAvailable = true;
        this.gpuName = r.platforms?.find(p => p.name.includes("CUDA"))?.name || "GPU";
      } else {
        this.gpuAvailable = false;
      }
      // Always use "auto" — the benchmark picks the fastest platform
      this.settings.platform = "auto";
      if (r.platform_warning) this.platformWarning = r.platform_warning;
      if (r.selected_platform) {
        this.liveLog.push(`Platform: ${r.selected_platform} (${usingGpu ? "GPU" : "CPU"} mode)`);
      }
    } catch (e) {
      this.platformWarning = "MD Lite backend unavailable: " + (e.message || "API error");
    }
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
      // Docking import → prepare_complex (protein + docked ligand on disk)
      if (this.inputMethod === "docking") {
        if (!this.dockingJob) {
          this.errorMessage = "Paste a docking job ID first";
          this.loading = false;
          return;
        }
        const imp = await callJsonApi("md_lite", { action: "import_docking", docking_job_id: this.dockingJob });
        if (imp.status === "error" || imp.error) {
          this.errorMessage = imp.error || "Import failed";
          this.loading = false;
          return;
        }
        this.jobId = imp.job_id;
        this.liveLog.push(`Docking files imported (job ${imp.job_id}). Preparing complex...`);
        const r = await callJsonApi("md_lite", {
          action: "prepare_complex",
          job_id: imp.job_id,
          forcefield: this.settings.forcefield,
          temperature: this.settings.temperature,
          platform: this.settings.platform,
        });
        if (r.status === "ok") {
          this.jobId = r.job_id || imp.job_id;
          this.step = 2;
          const atoms = r.total_atoms || ((r.protein_atoms || 0) + (r.ligand_atoms || 0));
          this.liveLog.push(`Complex prepared · ${atoms || "?"} atoms`);
        } else {
          this.errorMessage = r.error || "Prepare failed after docking import";
        }
        this.loading = false;
        return;
      }

      let p = {
        action: "prepare",
        forcefield: this.settings.forcefield,
        temperature: this.settings.temperature,
        platform: this.settings.platform,
      };
      if (this.inputMethod === "complex" && this._complexContent) {
        p.complex_pdb = this._complexContent;
      } else if (this.inputMethod === "separate" && this._proteinContent) {
        p.protein_pdb = this._proteinContent;
        if (this._ligandContent) p.ligand_sdf = this._ligandContent;
      } else {
        this.errorMessage = "Upload a PDB file first (complex or protein)";
        this.loading = false;
        return;
      }
      const r = await callJsonApi("md_lite", p);
      if (r.status === "ok") {
        this.jobId = r.job_id;
        this.step = 2;
        this.liveLog.push(`Minimization complete · ${r.min_energy_kjmol} kJ/mol`);
      } else {
        this.errorMessage = r.error || "Prepare failed";
      }
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
    this.loading = true; this.errorMessage = ""; this.liveLog = []; this.mdLog = [];
    try {
      const r = await callJsonApi("md_lite", {
        action: "run", job_id: this.jobId, total_ns: this.settings.total_ns,
        forcefield: this.settings.forcefield, temperature: this.settings.temperature,
        pressure: this.settings.pressure, platform: this.settings.platform,
        fast_mode: this.settings.fast_mode,
      });
      if (r.status === "ok") { this.platformWarning = r.platform_warning || ""; this.step = 3; this.startPolling(); }
      else { this.errorMessage = r.error || "Run failed"; }
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  startPolling() {
    this.liveLog.push("MD simulation started — " + (this.settings.fast_mode ? "fast mode" : "full mode"));
    this._lastProgress = 0;
    this._lastTime = Date.now();
    this.pollStatus();
    this._pollTimer = setInterval(() => this.pollStatus(), 3000);
    this._logPollTimer = setInterval(() => this.loadLog(), 8000);
  },

  async pollStatus() {
    if (!this.jobId) return;
    try {
      const r = await callJsonApi("md_lite", { action: "status", job_id: this.jobId });
      this.status = r;
      this.platformWarning = r.platform_warning || this.platformWarning || "";
      // Add phase changes to live log
      const phase = r.phase || r.status;
      if (phase && phase !== this._lastPhase) {
        this._lastPhase = phase;
        const label = this.phaseLabels[phase] || phase;
        if (r.status === "error") {
          this.liveLog.push(`❌ ${label}: ${r.error || "unknown error"}`);
        } else {
          this.liveLog.push(`▸ ${label}`);
        }
        if (this.liveLog.length > 30) this.liveLog.shift();
      }
      // Add chunks to live log when progress changes
      if (r.chunk && r.progress_pct !== this._lastProgress) {
        this._lastProgress = r.progress_pct;
        const eta = r.eta_minutes ? ` · ETA ${r.eta_minutes} min` : "";
        this.liveLog.push(`Segment ${r.chunk} · ${r.progress_ns} ns · ${r.progress_pct}%${eta}`);
        if (this.liveLog.length > 30) this.liveLog.shift();
      }
      if (r.status === "completed" || r.status === "error" || r.status === "stopped" || r.status === "interrupted") {
        clearInterval(this._pollTimer);
        clearInterval(this._logPollTimer);
        if (r.status === "completed") {
          this.liveLog.push("Simulation complete ✓");
          this.loadResults();
        } else if (r.status === "interrupted") {
          this.liveLog.push("⚠️ Simulation interrupted (system sleep or crash).");
          this.liveLog.push("Your partial trajectory and analysis are saved. Click Resume to continue, or Download to get what you have.");
          setTimeout(() => this.loadResults(), 500);
        }
      }
    } catch {}
  },

  async loadLog() {
    if (!this.jobId) return;
    try {
      const r = await callJsonApi("md_lite", { action: "log", job_id: this.jobId, lines: 20 });
      if (r.lines) this.mdLog = r.lines;
    } catch {}
  },

  async loadResults() {
    try {
      const r = await callJsonApi("md_lite", { action: "results", job_id: this.jobId });
      if (r.status === "error" || r.error) {
        this.errorMessage = "Analysis failed: " + (r.error || "unknown");
        this.liveLog.push("❌ Analysis: " + (r.error || "unknown"));
        return;
      }
      const analysis = r.analysis || r;
      if (analysis.error) {
        this.errorMessage = "Trajectory analysis: " + analysis.error;
        this.liveLog.push("❌ " + analysis.error);
        return;
      }
      this.result = analysis;
      this.result._metrics = [];
      if (this.result.rmsd && this.result.rmsd.final_nm != null) this.result._metrics.push({label:"RMSD", value:this.result.rmsd.final_nm+" nm", color:"#00d4aa"});
      if (this.result.rmsf && this.result.rmsf.max_nm != null) this.result._metrics.push({label:"RMSF", value:this.result.rmsf.max_nm+" nm", color:"#6366f1"});
      if (this.result.energy && this.result.energy.mean != null) this.result._metrics.push({label:"Energy", value:this.result.energy.mean+" kJ", color:"#f59e0b"});
      if (this.result.gyration && this.result.gyration.final_nm != null) this.result._metrics.push({label:"Rg", value:this.result.gyration.final_nm+" nm", color:"#8b5cf6"});
      if (this.result.sasa && this.result.sasa.final_nm2 != null) this.result._metrics.push({label:"SASA", value:this.result.sasa.final_nm2+" nm²", color:"#22c55e"});
      if (this.result.hbonds && this.result.hbonds.avg_per_frame != null) this.result._metrics.push({label:"H-Bonds", value:this.result.hbonds.avg_per_frame, color:"#f59e0b"});
      if (this.result._metrics.length === 0) {
        this.liveLog.push("⚠️ No analysis metrics available — trajectory may be too short");
      }
    } catch (e) {
      this.errorMessage = "Failed to load results: " + (e.message || "API error");
    }
  },

  async stopMD() {
    try {
      await callJsonApi("md_lite", { action: "stop", job_id: this.jobId });
      clearInterval(this._pollTimer);
      clearInterval(this._logPollTimer);
    } catch {}
  },

  async resumeMD() {
    if (!this.jobId) return;
    this.loading = true; this.errorMessage = "";
    try {
      const r = await callJsonApi("md_lite", {
        action: "resume", job_id: this.jobId,
        total_ns: this.settings.total_ns, platform: this.settings.platform,
      });
      if (r.status === "ok") {
        this.liveLog.push("Resumed from checkpoint ✓");
        this.startPolling();
      } else {
        this.errorMessage = r.error || "Resume failed";
      }
    } catch (e) { this.errorMessage = "Resume: " + (e.message || "API error"); }
    this.loading = false;
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

  async runAdvancedAnalysis() {
    this.advancedLoading = true; this.advancedResult = null; this.errorMessage = "";
    this.showAdvanced = true;
    try {
      const r = await callJsonApi("md_lite", { action: "analyze_advanced", job_id: this.jobId });
      this.advancedResult = r;
      if (r.status !== "ok" && r.error) this.errorMessage = r.error;
    } catch (e) { this.errorMessage = "Advanced analysis: " + (e.message || "API unavailable"); }
    this.advancedLoading = false;
  },

  resetAll() {
    clearInterval(this._pollTimer);
    clearInterval(this._logPollTimer);
    this.step = 1; this.jobId = null;
    this.result = null; this.status = null; this.errorMessage = "";
    this.liveLog = []; this.mdLog = [];
    this.platformWarning = ""; this._lastPhase = null;
    this.mmpbsaResult = null; this.mmpbsaLoading = false;
    this._complexContent = null; this._proteinContent = null; this._ligandContent = null;
    this._complexName = ""; this._proteinName = ""; this._ligandName = "";
  },
});

function registerMdLite() {
  if (globalThis.Alpine?.data) {
    globalThis.Alpine.data("mdLite", mdLiteFactory);
  }
}
if (globalThis.Alpine) registerMdLite();
else document.addEventListener("alpine:init", registerMdLite);
