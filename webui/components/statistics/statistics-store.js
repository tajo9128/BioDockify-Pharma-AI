import { callJsonApi } from "/js/api.js";

const SLOT_LAYOUT = {
  ttest:          { value: "Dependent (N)", group: "Group (G, 2 levels)" },
  anova:          { value: "Dependent (N)", group: "Group (G, 3+ levels)" },
  correlation:    { cols: "Select 2+ columns (N)" },
  descriptive:    {},
  chisquare:      { rows: "Row Variable (C)", cols: "Column Variable (C)" },
  mannwhitney:    { value: "Dependent (N)", group: "Group (G, 2 levels)" },
  wilcoxon:       { before: "Before (N)", after: "After (N)" },
  kruskalwallis:  { value: "Dependent (N)", group: "Group (G, 3+ levels)" },
  friedman:       { cols: "Select 3+ columns (N) — per timepoint" },
  fisher:         { rows: "Row (C)", cols: "Column (C)" },
  normality:      { value: "Select column (N)" },
  homogeneity:    { value: "Dependent (N)", group: "Group (G)" },
  roc:            { labels: "True Labels (binary)", scores: "Predicted Scores (N)" },
  power:          {},
  survival:       {},
  regression:     {},
  factor:         { cols: "Select 2+ columns (N)" },
  reliability:    { cols: "Select 3+ columns (N)" },
  cluster:        { cols: "Select 2+ columns (N)" },
};

Alpine.data("statisticsModal", () => ({
  step: 1, fileName: "", columns: [], rowCount: 0,
  summary: null, testType: "", loading: false, errorMessage: "", result: null,

  // Phase 1: Editable data table
  dataRows: [], isDirty: false, showTable: false,
  pageSize: 50, currentPage: 1,
  get visibleRows() { return this.dataRows.slice((this.currentPage-1)*this.pageSize, this.currentPage*this.pageSize); },
  get totalPages() { return Math.max(1, Math.ceil(this.dataRows.length / this.pageSize)); },
  nextPage() { if (this.currentPage < this.totalPages) this.currentPage++; },
  prevPage() { if (this.currentPage > 1) this.currentPage--; },

  // Phase 2: Variable assignment
  slots: { value: "", group: "", before: "", after: "", rows: "", cols: "", labels: "", scores: "" },
  activeSlot: null,

  // Phase 3: Live update
  liveMode: true,

  // Phase 6: Results history
  history: [],

  init() {
    // Phase 3: Live update watchers
    this.$watch("slots", () => this.debouncedRun());
    this.$watch("testType", () => { this.slots = { value:"", group:"", before:"", after:"", rows:"", cols:"", labels:"", scores:"" }; this.activeSlot = null; this.result = null; this.debouncedRun(); });
    this._restore();
  },

  // ============== PHASE 1: Editable Table ==============
  toggleTable() { this.showTable = !this.showTable; },
  updateCell(ri, ci, val) { this.isDirty = true; },
  addRow() { this.dataRows.push(this.columns.map(() => "")); this.isDirty = true; },
  deleteRow(ri) { this.dataRows.splice(ri, 1); this.rowCount = this.dataRows.length; this.isDirty = true; if (this.currentPage > this.totalPages) this.currentPage = this.totalPages; },
  async reAnalyze() {
    this.loading = true; this.errorMessage = ""; this.isDirty = false;
    try {
      const csv = [this.columns.join(","), ...this.dataRows.map(r => r.join(","))].join("\n");
      const r = await callJsonApi("statistics_auto", { action: "analyze", content: csv, filename: this.fileName });
      if (r.status === "ok") {
        this.summary = r; this.columns = r.data_summary?.column_names || [];
        this.rowCount = r.data_summary?.total_rows || 0;
        this.testType = r.recommended_test || "";
      } else { this.errorMessage = r.error || "Re-analysis failed"; }
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  // ============== PHASE 2: Variable Assignment ==============
  get SLOT_LAYOUT() { return SLOT_LAYOUT; },
  slotLabels() { return SLOT_LAYOUT[this.testType] || {}; },
  assignColumn(col) {
    if (!this.activeSlot) return;
    this.slots[this.activeSlot] = col;
    this.activeSlot = null;
  },
  clearSlot(slot) { this.slots[slot] = ""; },
  isAssigned(col) { return Object.values(this.slots).includes(col); },
  isTestReady() {
    const layout = SLOT_LAYOUT[this.testType];
    if (!layout || !Object.keys(layout).length) return true; // tests with no slots
    return Object.keys(layout).every(s => this.slots[s]);
  },
  get colTypes() { return this.columns.map(c => ({ name: c, type: this._colType(c) })); },
  _colType(col) { return this.summary?.data_summary?.group_columns?.includes(col) ? "G" : this.summary?.data_summary?.numeric_columns?.includes(col) ? "N" : "C"; },

  // ============== PHASE 3: Live Update ==============
  debouncedRun() {
    clearTimeout(this._timer);
    if (!this.liveMode || this.step !== 2) return;
    if (this.isTestReady() && this.testType) {
      this._timer = setTimeout(() => this.runSelectedTest(), 300);
    }
  },
  toggleLive() { this.liveMode = !this.liveMode; if (this.liveMode) this.debouncedRun(); },

  // ============== MAIN FLOW ==============
  openFilePicker() {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".csv,.xlsx,.xls,.json"; input.style.display = "none";
    input.onchange = e => { const f = e.target.files?.[0]; input.remove(); if (f) this.processUpload(f); };
    document.body.appendChild(input); input.click();
  },
  handleDrop(e) { const f = e.dataTransfer?.files?.[0]; if (f) this.processUpload(f); },

  async processUpload(file) {
    this.loading = true; this.errorMessage = ""; this.fileName = file.name;
    this.summary = null; this.result = null; this.history = [];
    try {
      const { content } = await this.readContent(file);
      const r = await callJsonApi("statistics_auto", { action: "analyze", content, filename: file.name });
      if (r.status === "ok") {
        this.summary = r; this.columns = r.data_summary?.column_names || [];
        this.rowCount = r.data_summary?.total_rows || 0;
        // Phase 1: Store raw data for editable table
        this.dataRows = this._parseRawRows(content, r.data_summary?.column_names || []);
        this.isDirty = false; this.showTable = false; this.currentPage = 1;
        this.step = 2; this.testType = r.recommended_test || "";
      } else { this.errorMessage = r.error || "Upload failed"; }
    } catch (e) { this.errorMessage = "Upload error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  _parseRawRows(content, cols) {
    try {
      if (!content || content.length < 5) return [];
      // Only parse CSV — XLSX/JSON handled by backend parse in _analyze
      if (this.fileName.endsWith(".xlsx") || this.fileName.endsWith(".xls") || this.fileName.endsWith(".json")) return [];
      const lines = content.split("\n").filter(l => l.trim());
      if (lines.length < 2) return [];
      const rows = [];
      for (let i = 1; i < lines.length; i++) {
        rows.push(lines[i].split(",").map(v => v.trim().replace(/^"|"$/g, "")));
      }
      return rows.slice(0, 500);
    } catch { return []; }
  },

  readContent(file) {
    const ext = (file.name || "").split(".").pop().toLowerCase();
    if (ext === "xlsx" || ext === "xls") {
      return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => {
          const b = new Uint8Array(r.result); let s = "";
          for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, Math.min(i + 8192, b.length)));
          resolve({ content: btoa(s), isBinary: true });
        };
        r.onerror = () => reject(new Error("Read failed"));
        r.readAsArrayBuffer(file);
      });
    }
    return file.text().then(t => ({ content: t, isBinary: false }));
  },

  async runSelectedTest() {
    if (!this.testType) { this.errorMessage = "Select a test type"; return; }
    this.loading = true; this.errorMessage = ""; this.result = null;
    try {
      const r = await callJsonApi("statistics_analyze", {
        action: "auto_decide",
        test_type: this.testType,
        columns: this.columns,
        summary: this.summary?.data_summary || {},
        slots: this.slots,
        data: this.dataRows,
      });
      if (r.status === "ok") {
        this.result = r; this.step = 3;
        // Phase 6: Add to history
        this.history.unshift({ id: Date.now(), type: this.testType, summary: r.test_name || this.testType, result: r });
        if (this.history.length > 20) this.history.pop();
      } else { this.errorMessage = r.error || "Analysis failed"; }
    } catch (e) { this.errorMessage = "Analysis error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  showHistoryResult(h) { this.result = h.result; this.step = 3; },
  removeFromHistory(id) { this.history = this.history.filter(h => h.id !== id); },

  // Navigation
  resetData() {
    this.step = 1; this.fileName = ""; this.columns = []; this.rowCount = 0;
    this.summary = null; this.testType = ""; this.result = null; this.errorMessage = "";
    this.dataRows = []; this.isDirty = false; this.showTable = false; this.currentPage = 1;
    this.slots = { value:"", group:"", before:"", after:"", rows:"", cols:"", labels:"", scores:"" };
    this.activeSlot = null; this.history = [];
  },
  goBack() { this.step = 2; this.result = null; },

  // Save/Export
  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry(`${this.testType} — ${this.fileName}`, JSON.stringify(this.result, null, 2), "Statistical Analysis", ["statistics", this.testType]);
    }
  },
  downloadJSON() {
    if (!this.result) return;
    const b = new Blob([JSON.stringify(this.result, null, 2)], { type: "application/json" });
    const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = "stats-result.json"; a.click(); URL.revokeObjectURL(u);
  },
  exportAll() {
    const b = new Blob([JSON.stringify(this.history.map(h => ({ type: h.type, result: h.result })), null, 2)], { type: "application/json" });
    const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = "all-results.json"; a.click(); URL.revokeObjectURL(u);
  },

  // Persistence
  _restore() {
    try {
      const s = JSON.parse(localStorage.getItem("biodockify.statistics") || "{}");
      if (s.fileName && s.columns?.length) { this.fileName = s.fileName; this.columns = s.columns; this.rowCount = s.rowCount || 0; this.step = 2; }
      if (s.testType) this.testType = s.testType;
    } catch {}
  },
  _persist() {
    try { localStorage.setItem("biodockify.statistics", JSON.stringify({ fileName: this.fileName, columns: this.columns, rowCount: this.rowCount, testType: this.testType })); } catch {}
  },
}));
