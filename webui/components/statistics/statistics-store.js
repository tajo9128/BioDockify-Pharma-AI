import { callJsonApi } from "/js/api.js";

Alpine.data("statisticsModal", () => ({
  step: 1,
  hasData: false,
  fileName: "",
  columns: [],
  rowCount: 0,
  _restored: false,
  transformMode: "",       // compute, recode, rank, fill, standardize
  transformFormula: "",
  transformColumn: "",
  transformTarget: "",

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
  clusterK: 3,
  clusterMethod: "kmeans",

  results: "",
  resultsJson: null,
  loading: false,
  activeAnalysis: "",
  viewMode: "table",
  chartImage: null,
  chartLoading: false,
  rawData: null,         // Raw numeric data arrays for factor/reliability/cluster
  errorMessage: "",

  async _parseLocalFile(file) {
    try {
      const text = await file.text();
      if (file.name.endsWith(".json")) {
        const obj = JSON.parse(text);
        const arr = Array.isArray(obj) ? obj : (obj.data || Object.values(obj)[0]);
        this._extractColumns(arr);
      } else {
        // CSV parsing
        const lines = text.split("\n").filter(l => l.trim());
        if (lines.length < 2) return;
        const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
          const vals = lines[i].split(",").map(v => {
            const cleaned = v.trim().replace(/^"|"$/g, "");
            const n = parseFloat(cleaned);
            return isNaN(n) ? cleaned : n;
          });
          rows.push(vals);
        }
        this._setRawData(headers, rows);
      }
    } catch (e) {}
  },

  _extractColumns(arr) {
    if (!arr || !arr.length) return;
    const cols = Object.keys(arr[0]);
    this._setRawData(cols, arr.map(r => cols.map(c => r[c])));
  },

  _setRawData(headers, rows) {
    const numericCols = [];
    const data = [];
    for (let ci = 0; ci < headers.length; ci++) {
      const col = [];
      for (const row of rows) {
        const v = row[ci];
        if (typeof v === "number" && !isNaN(v)) col.push(v);
      }
      if (col.length > 1) {
        numericCols.push(ci);
        data.push(col);
      }
    }
    if (data.length > 0) {
      const minLen = Math.min(...data.map(c => c.length));
      const aligned = data.map(c => c.slice(0, minLen));
      // Transpose: columns → rows for API
      const result = [];
      for (let i = 0; i < minLen; i++) {
        const row = [];
        for (let j = 0; j < aligned.length; j++) {
          row.push(aligned[j][i]);
        }
        result.push(row);
      }
      this.rawData = result;
    }
  },

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

  selectTest(type) { this.testType = type; this.results = ""; this.resultsJson = null; this.errorMessage = ""; this.activeAnalysis = ""; this.persist(); },

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
        const content = await file.text();
        const data = await callJsonApi("statistics_import", {
          action: "import_file",
          content: content,
          filename: file.name,
        });
        if (data.status === "success" || data.data_summary) {
          const summary = data.data_summary || data;
          this.columns = summary.column_names || [];
          this.rowCount = summary.rows || 0;
          this.hasData = true;
          this.step = 2;
          this._parseLocalFile(file);
          this.results = "";
          this.errorMessage = "";
          this.persist();
        } else {
          this.errorMessage = "Import failed: " + (data.detail || data.error || "Unknown error");
        }
      } catch (e) { this.errorMessage = "Import error: " + e.message; }
      this.loading = false;
    };
    input.click();
  },

  async runAnalysis() {
    if (!this.testType) { this.errorMessage = "Select an analysis type first"; return; }
    this.activeAnalysis = this.testType;
    this.loading = true;
    this.results = "";
    this.errorMessage = "";
    try {
      let endpoint = "";
      let payload = {};
      switch (this.testType) {
        case "descriptive": endpoint = "statistics/analyze/descriptive"; break;
        case "correlation":
          if (this.selectedCorrCols.length < 2) { this.errorMessage = "Select at least 2 columns for correlation"; this.loading = false; return; }
          endpoint = "statistics/analyze/correlation";
          payload = { columns: this.selectedCorrCols, method: this.correlationMethod }; break;
        case "ttest":
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select both Group and Value columns"; this.loading = false; return; }
          endpoint = "statistics/analyze/t-test";
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol, test_type: this.ttestType, equal_var: this.ttestEqualVar }; break;
        case "anova":
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select both Group and Value columns for ANOVA"; this.loading = false; return; }
          endpoint = "statistics/analyze/anova";
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol, post_hoc: this.anovaPostHoc }; break;
        case "regression":
        case "survival":
        case "pkpd":
          this.errorMessage = "This analysis runs via the AI agent. Ask in the chat panel.";
          this.loading = false; return;
        case "power":
          endpoint = "statistics/analyze/power";
          payload = { test_type: "ttest_ind", effect_size: this.powerEffectSize, alpha: this.powerAlpha, power: this.powerTarget }; break;
        case "factor":
          endpoint = "statistics_reduction";
          payload = { action: "factor", data: this.rawData || [], columns: this.columns, n_components: null }; break;
        case "reliability":
          endpoint = "statistics_reduction";
          payload = { action: "reliability", data: this.rawData || [], columns: this.columns }; break;
        case "cluster":
          endpoint = "statistics_reduction";
          payload = { action: this.clusterMethod === "hierarchical" ? "cluster_hierarchical" : "cluster_kmeans",
                       data: this.rawData || [], columns: this.columns, n_clusters: this.clusterK || 3,
                       method: this.clusterMethod === "hierarchical" ? "ward" : undefined }; break;
        case "chisquare":
          endpoint = "statistics/analyze/chi-square-independence";
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol }; break;
        case "mannwhitney":
          endpoint = "statistics/analyze/mann-whitney";
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol }; break;
        case "wilcoxon":
          endpoint = "statistics/analyze/wilcoxon-signed-rank";
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol }; break;
        case "kruskalwallis":
          endpoint = "statistics/analyze/kruskal-wallis";
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol }; break;
        case "friedman":
          endpoint = "statistics/analyze/friedman";
          payload = { data: this.rawData || [], columns: this.columns }; break;
        case "fisher":
          endpoint = "statistics/analyze/fisher-exact";
          payload = { data: this.rawData || [], columns: this.columns }; break;
        case "normality":
          endpoint = "statistics/diagnostic/normality";
          payload = { data: this.rawData || [], columns: this.columns }; break;
        case "homogeneity":
          endpoint = "statistics/diagnostic/homogeneity";
          if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
          payload = { group_col: this.selectedGroupCol, value_col: this.selectedValueCol }; break;
        case "roc":
          endpoint = "statistics_advanced";
          payload = { action: "roc", y_true: this.rawData?.[0] || [], y_score: this.rawData?.[1] || [] }; break;
        default: this.errorMessage = "Unknown analysis type"; this.loading = false; return;
      }
      const result = await callJsonApi(endpoint, payload);
      this.resultsJson = result;
      this.results = JSON.stringify(result, null, 2);
      this.step = 3;
      this.chartImage = null;
      // Auto-generate chart
      this.generateChart();
    } catch (e) {
      this.errorMessage = "Analysis failed: " + (e.message || "API unavailable. Try asking the agent instead.");
    }
    this.loading = false;
  },

  async generateChart() {
    if (!this.resultsJson) return;
    this.chartLoading = true;
    this.chartImage = null;
    const data = this.resultsJson;
    try {
      let payload = { chart_type: "histogram", title: this.activeAnalysis };
      // Detect best chart type from result structure
      if (data.eigenvalues) {
        // PCA — use scree plot from result itself
        this.chartImage = data.scree_plot || null;
        this.chartLoading = false;
        return;
      }
      if (data.dendrogram) {
        this.chartImage = data.dendrogram;
        this.chartLoading = false;
        return;
      }
      if (data.roc || data.auc !== undefined) {
        payload = { chart_type: "roc", fpr: data.fpr || [], tpr: data.tpr || [], auc: data.auc, title: "ROC Curve (AUC=" + (data.auc || 0).toFixed(3) + ")" };
      } else if (data.survival || data.times) {
        payload = { chart_type: "survival", times: data.times || [], survival: data.survival || [], title: "Survival Curve" };
      } else if (data.correlation_matrix) {
        const cols = data.columns || [];
        payload = { chart_type: "correlation_heatmap", matrix: data.correlation_matrix, labels: cols, title: "Correlation Matrix" };
      } else if (data.anova_table || data.f_statistic !== undefined) {
        const groups = data.group_means || {};
        payload = { chart_type: "boxplot", groups: groups, title: "Group Comparison" };
      } else if (data.coefficients || data.r_squared !== undefined) {
        payload = { chart_type: "scatter", x: data.x || data.fitted || [], y: data.y || data.y_actual || [], title: "Fit Plot", x_label: "Predicted", y_label: "Actual" };
      } else if (data.fpr) {
        payload = { chart_type: "roc", fpr: data.fpr, tpr: data.tpr, auc: data.auc, title: "ROC Curve" };
      } else if (data.values || data.data) {
        payload = { chart_type: "histogram", values: data.values || data.data, title: this.activeAnalysis };
      } else {
        payload = { chart_type: "bar", labels: Object.keys(data.results || data).slice(0, 10), values: Object.values(data.results || data).slice(0, 10).map(v => typeof v === "number" ? v : 0), title: this.activeAnalysis };
      }
      const r = await callJsonApi("statistics_charts", payload);
      if (r.success && r.chart) this.chartImage = r.chart;
    } catch (e) {}
    this.chartLoading = false;
  },

  downloadChart() {
    if (!this.chartImage) return;
    const a = document.createElement("a");
    a.href = "data:image/png;base64," + this.chartImage;
    a.download = (this.activeAnalysis || "chart") + ".png";
    a.click();
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
    this.testType = null; this.results = ""; this.resultsJson = null; this.errorMessage = "";
    this.activeAnalysis = ""; this.viewMode = "table";
  },

  sendToAgent(prompt) {
    const input = document.getElementById("chat-input");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
    }
  },

  async handleDrop(event) {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    this.loading = true; this.fileName = file.name;
    try {
      const content = await file.text();
      const d = await callJsonApi("statistics_import", { action: "import_file", content: content, filename: file.name });
      const s = d.data_summary || d;
      this.columns = s.column_names || []; this.rowCount = s.rows || 0;
      this.hasData = true; this.step = 2;
      this.persist();
    } catch (e) { this.errorMessage = "Import error: " + e.message; }
    this.loading = false;
  },

  closeModal() { this.resetData(); globalThis.closeModal(); },

  useSampleData() {
    this.fileName = "sample-data.csv";
    this.columns = ["Treatment", "Response", "Weight", "Age", "Dose", "Score", "Group", "Time"];
    this.rowCount = 100;
    this.hasData = true;
    this.step = 2;
  },
}));
