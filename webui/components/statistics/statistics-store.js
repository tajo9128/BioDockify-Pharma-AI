import { callJsonApi } from "/js/api.js";

Alpine.data("statisticsModal", () => ({
  step: 1,
  hasData: false,
  fileName: "",
  columns: [],
  rowCount: 0,
  _restored: false,

  testType: null,
  selectedGroupCol: "",
  selectedValueCol: "",
  selectedCorrCols: [],
  correlationMethod: "pearson",
  anovaPostHoc: true,
  ttestType: "independent",
  ttestEqualVar: true,
  powerEffectSize: 0.5,
  powerAlpha: 0.05,
  powerTarget: 0.80,

  results: "",
  resultsJson: null,
  loading: false,
  activeAnalysis: "",
  viewMode: "table",

  persist() {
    try {
      localStorage.setItem("biodockify.statistics", JSON.stringify({
        fileName: this.fileName, columns: this.columns, rowCount: this.rowCount,
        testType: this.testType, selectedGroupCol: this.selectedGroupCol,
        selectedValueCol: this.selectedValueCol, correlationMethod: this.correlationMethod,
      }));
    } catch {}
  },

  restore() {
    if (this._restored) return;
    this._restored = true;
    try {
      const s = JSON.parse(localStorage.getItem("biodockify.statistics") || "{}");
      if (s.fileName) { this.fileName = s.fileName; this.columns = s.columns || []; this.rowCount = s.rowCount || 0; this.hasData = true; this.step = 2; }
      if (s.testType) this.testType = s.testType;
      if (s.selectedGroupCol) this.selectedGroupCol = s.selectedGroupCol;
      if (s.selectedValueCol) this.selectedValueCol = s.selectedValueCol;
      if (s.correlationMethod) this.correlationMethod = s.correlationMethod;
    } catch {}
  },

  get columnOptions() { return this.columns.map(c => ({ value: c, label: c })); },

  selectTest(type) { this.testType = type; this.results = ""; this.resultsJson = null; this.persist(); },

  async importData() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx,.xls,.json";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      this.loading = true;
      this.fileName = file.name;
      try {
        const formData = new FormData();
        formData.append("file", file);
        const resp = await fetch("/api/statistics/import-data", {
          method: "POST", body: formData,
          headers: { "X-CSRF-Token": await getCsrfToken() }
        });
        const data = await resp.json();
        if (data.status === "success" || data.data_summary) {
          const summary = data.data_summary || data;
          this.columns = summary.column_names || [];
          this.rowCount = summary.rows || 0;
          this.hasData = true;
          this.step = 2;
          this.results = "";
          this.persist();
        } else {
          this.results = "Import failed: " + (data.detail || data.error || "Unknown error");
        }
      } catch (e) { this.results = "Import error: " + e.message; }
      this.loading = false;
    };
    input.click();
  },

  async runAnalysis() {
    if (!this.testType) return;
    this.activeAnalysis = this.testType;
    this.loading = true;
    this.results = "";
    try {
      let endpoint = "";
      let payload = {};
      switch (this.testType) {
        case "descriptive": endpoint = "statistics/analyze/descriptive"; break;
        case "correlation":
          if (this.selectedCorrCols.length < 2) { this.results = "Select at least 2 columns"; this.loading = false; return; }
          endpoint = "statistics/analyze/correlation";
          payload = { columns: this.selectedCorrCols, method: this.correlationMethod }; break;
        case "ttest":
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.results = "Select Group and Value columns"; this.loading = false; return; }
          endpoint = "statistics/analyze/t-test";
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol, test_type: this.ttestType, equal_var: this.ttestEqualVar }; break;
        case "anova":
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.results = "Select Group and Value columns"; this.loading = false; return; }
          endpoint = "statistics/analyze/anova";
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol, post_hoc: this.anovaPostHoc }; break;
        case "regression":
        case "survival":
        case "pkpd":
          this.results = `${this.testType}: Use agent chat for this analysis type`;
          this.loading = false; return;
        case "power":
          endpoint = "statistics/analyze/power";
          payload = { test_type: "ttest_ind", effect_size: this.powerEffectSize, alpha: this.powerAlpha, power: this.powerTarget }; break;
        default: this.results = "Unknown analysis"; this.loading = false; return;
      }
      const result = await callJsonApi(endpoint, payload);
      this.resultsJson = result;
      this.results = JSON.stringify(result, null, 2);
      this.step = 3;
    } catch (e) { this.results = "Error: " + e.message; }
    this.loading = false;
  },

  formatTable(json) {
    if (!json) return "";
    try {
      const data = typeof json === "string" ? JSON.parse(json) : json;
      const r = data?.results || data;
      const keys = Object.keys(r || {});
      if (!keys.length) return "";
      let h = "<table><thead><tr>";
      keys.forEach(k => { h += `<th>${k}</th>`; });
      h += "</tr></thead><tbody><tr>";
      keys.forEach(k => {
        const v = r[k];
        h += `<td>${typeof v === "number" ? v.toFixed(4) : String(v)}</td>`;
      });
      h += "</tr></tbody></table>";
      return h;
    } catch { return ""; }
  },

  downloadResults(format) {
    if (!this.resultsJson && !this.results) return;
    const data = this.resultsJson || (typeof this.results === "string" ? JSON.parse(this.results) : this.results);
    let content = JSON.stringify(data, null, 2), mime = "application/json", ext = "json";
    if (format === "csv") {
      content = "key,value\n";
      const r = data?.results || data;
      for (const [k, v] of Object.entries(r || {})) content += `${k},${v}\n`;
      mime = "text/csv"; ext = "csv";
    }
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `statistics-results.${ext}`;
    a.click(); URL.revokeObjectURL(url);
  },

  copyResults() {
    if (!this.results) return;
    navigator.clipboard.writeText(this.results);
  },

  saveToNotebook() {
    if (!this.resultsJson && !this.results) return;
    const title = `${this.activeAnalysis || "Analysis"} on ${this.fileName || "data"}`;
    const content = this.results || JSON.stringify(this.resultsJson || {}, null, 2);
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry) {
      $store.knowledgeModal.addNoteBookEntry(title, content, "Statistical Analysis", ["statistics", this.activeAnalysis || "analysis"]);
    }
  },

  resetData() {
    this.hasData = false; this.step = 1; this.fileName = ""; this.columns = []; this.rowCount = 0;
    this.selectedGroupCol = ""; this.selectedValueCol = ""; this.selectedCorrCols = [];
    this.testType = null; this.results = ""; this.resultsJson = null;
    this.activeAnalysis = ""; this.viewMode = "table";
  },

  sendToAgent(prompt) {
    const input = document.querySelector("#chat-bar-input textarea, .chat-bar-input textarea, .input-area textarea");
    if (input) { input.value = prompt; input.dispatchEvent(new Event("input", { bubbles: true })); input.focus(); }
  },

  handleDrop(event) {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    this.loading = true; this.fileName = file.name;
    const fd = new FormData(); fd.append("file", file);
    fetch("/api/statistics/import-data", { method: "POST", body: fd, headers: { "X-CSRF-Token": getCsrfToken() } })
      .then(r => r.json()).then(d => {
        const s = d.data_summary || d;
        this.columns = s.column_names || []; this.rowCount = s.rows || 0;
        this.hasData = true; this.step = 2;
      }).catch(e => { this.results = "Import error: " + e.message; })
      .finally(() => { this.loading = false; });
  },

  closeModal() { this.resetData(); closeTopModal(); },
}));

async function getCsrfToken() {
  try { const r = await fetch("/api/csrf_token"); const j = await r.json(); return j.token; }
  catch { return ""; }
}
