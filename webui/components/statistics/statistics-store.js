import { callJsonApi } from "/js/api.js";

Alpine.data("statisticsModal", () => ({
  step: 1,
  hasData: false,
  fileName: "",
  columns: [],
  rowCount: 0,
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
  viewMode: "auto",
  rawData: null,
  errorMessage: "",
  autoResult: null,

  // === File reading ===
  readFileContent(file) {
    const ext = (file.name || "").split(".").pop().toLowerCase();
    if (ext === "xlsx" || ext === "xls") {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const bytes = new Uint8Array(reader.result);
          let binary = "";
          const chunk = 8192;
          for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunk, bytes.length)));
          }
          resolve({ content: btoa(binary), isBinary: true });
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsArrayBuffer(file);
      });
    }
    return file.text().then(text => ({ content: text, isBinary: false }));
  },

  // === Upload: auto-analyze a file ===
  async processFile(file) {
    if (!file) return;
    this.loading = true;
    this.errorMessage = "";
    this.autoResult = null;
    this.fileName = file.name;
    try {
      const { content } = await this.readFileContent(file);
      const result = await callJsonApi("statistics_auto", {
        action: "auto_analyze",
        content: content,
        filename: file.name,
      });
      if (result.status === "ok") {
        this.autoResult = result;
        this.columns = result.data_summary?.column_names || [];
        this.rowCount = result.data_summary?.total_rows || 0;
        this.hasData = true;
        this.step = 3;
        this.results = JSON.stringify(result, null, 2);
        this.resultsJson = result;
        this.activeAnalysis = "Auto-Analyze";
        this.viewMode = "auto";
        this._buildRawDataFromContent(content, file.name);
        this._storeToKB(result);
        this.persist();
      } else {
        this.errorMessage = result.error || "Analysis failed";
      }
    } catch (e) {
      this.errorMessage = "Upload error: " + (e.message || "API unavailable");
    }
    this.loading = false;
  },

  _buildRawDataFromContent(content, filename) {
    try {
      if (filename.endsWith(".json")) {
        const obj = JSON.parse(content);
        const arr = Array.isArray(obj) ? obj : (obj.data || Object.values(obj)[0] || []);
        if (arr.length) this._extractNumeric(arr);
      } else {
        const lines = content.split("\n").filter(l => l.trim());
        if (lines.length < 2) return;
        const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
          rows.push(lines[i].split(",").map(v => {
            const c = v.trim().replace(/^"|"$/g, "");
            const n = parseFloat(c);
            return isNaN(n) ? c : n;
          }));
        }
        this._extractNumeric(rows.map(r => {
          const o = {};
          headers.forEach((h, i) => o[h] = r[i]);
          return o;
        }));
      }
    } catch (e) { /* best effort */ }
  },

  _extractNumeric(items) {
    const cols = Object.keys(items[0] || {});
    const data = [];
    for (const col of cols) {
      const vals = [];
      for (const item of items) {
        const v = item[col];
        if (typeof v === "number" && !isNaN(v)) vals.push(v);
      }
      if (vals.length > 1) data.push(vals);
    }
    if (data.length) {
      const minLen = Math.min(...data.map(c => c.length));
      this.rawData = data.map(c => c.slice(0, minLen))[0]
        ? data[0].map((_, i) => data.map(c => c[i]))
        : [];
    }
  },

  // === Sample Data ===
  useSampleData() {
    this.fileName = "sample-data.csv";
    this.columns = ["Treatment", "Response", "Weight", "Age", "Dose", "Score", "Group"];
    this.rowCount = 50;
    this.hasData = true;
    this.step = 2;
    const gens = {
      "Treatment": () => Math.random() > 0.5 ? "A" : "B",
      "Response": () => +(Math.random() * 20 + 50 + (Math.random() > 0.5 ? 5 : -5)).toFixed(2),
      "Weight": () => +(Math.random() * 30 + 60).toFixed(1),
      "Age": () => Math.floor(Math.random() * 40 + 25),
      "Dose": () => +(Math.random() * 5 + 1).toFixed(1),
      "Score": () => +(Math.random() * 30 + 60).toFixed(1),
      "Group": () => Math.floor(Math.random() * 3 + 1),
    };
    const rows = [];
    for (let i = 0; i < 50; i++) rows.push(this.columns.map(c => gens[c]()));
    this._setRawArray(this.columns, rows);
    this.persist();
  },

  _setRawArray(headers, rows) {
    const data = [];
    for (const col of headers) {
      const vals = [];
      for (const row of rows) {
        const ci = headers.indexOf(col);
        const v = row[ci];
        if (typeof v === "number" && !isNaN(v)) vals.push(v);
      }
      if (vals.length > 1) data.push(vals);
    }
    if (data.length) {
      const minLen = Math.min(...data.map(c => c.length));
      const aligned = data.map(c => c.slice(0, minLen));
      this.rawData = aligned[0].map((_, i) => aligned.map(c => c[i]));
    }
    this.columns = headers;
  },

  // === Upload trigger ===
  openFilePicker() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx,.xls,.json";
    input.style.display = "none";
    input.onchange = (e) => {
      const file = e.target.files?.[0];
      input.remove();
      if (file) this.processFile(file);
    };
    document.body.appendChild(input);
    input.click();
  },

  handleDrop(e) {
    const file = e.dataTransfer?.files?.[0];
    if (file) this.processFile(file);
  },

  // === Manual test execution ===
  selectTest(type) {
    this.testType = type;
    this.results = "";
    this.resultsJson = null;
    this.errorMessage = "";
    this.activeAnalysis = "";
    this.persist();
  },

  async runAnalysis() {
    if (!this.testType) { this.errorMessage = "Select an analysis type first"; return; }
    this.activeAnalysis = this.testType;
    this.loading = true;
    this.results = "";
    this.errorMessage = "";
    try {
      let endpoint = "statistics_analyze";
      let payload = { action: this.testType, columns: this.columns };

      const tt = this.testType;
      if (tt === "descriptive") {
        payload = { action: "descriptive", data: this.rawData || [], columns: this.columns };
      } else if (tt === "correlation") {
        if (this.selectedCorrCols.length < 2) { this.errorMessage = "Select at least 2 columns"; this.loading = false; return; }
        payload = { action: "correlation", data: this.rawData || [], columns: this.columns, selected_cols: this.selectedCorrCols, method: this.correlationMethod };
      } else if (tt === "ttest") {
        if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
        payload = { action: "ttest", data: this.rawData || [], columns: this.columns, group_col: this.selectedGroupCol, value_col: this.selectedValueCol, test_type: this.ttestType, equal_var: this.ttestEqualVar };
      } else if (tt === "anova") {
        if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
        payload = { action: "anova", data: this.rawData || [], columns: this.columns, group_col: this.selectedGroupCol, value_col: this.selectedValueCol, post_hoc: this.anovaPostHoc };
      } else if (tt === "chisquare" || tt === "mannwhitney" || tt === "wilcoxon" || tt === "kruskalwallis" || tt === "homogeneity") {
        if (!this.selectedGroupCol || !this.selectedValueCol) { this.errorMessage = "Select Group and Value columns"; this.loading = false; return; }
        payload = { action: tt, data: this.rawData || [], columns: this.columns, group_col: this.selectedGroupCol, value_col: this.selectedValueCol };
      } else if (tt === "friedman" || tt === "fisher" || tt === "normality") {
        payload = { action: tt, data: this.rawData || [], columns: this.columns };
      } else if (tt === "power") {
        payload = { action: "power", test_type: "ttest_ind", effect_size: this.powerEffectSize, alpha: this.powerAlpha, power: this.powerTarget };
      } else if (tt === "factor" || tt === "reliability") {
        endpoint = "statistics_reduction";
        payload = { action: tt, data: this.rawData || [], columns: this.columns };
      } else if (tt === "cluster") {
        endpoint = "statistics_reduction";
        payload = { action: this.clusterMethod === "hierarchical" ? "cluster_hierarchical" : "cluster_kmeans", data: this.rawData || [], columns: this.columns, n_clusters: this.clusterK };
      } else if (tt === "roc") {
        endpoint = "statistics_advanced";
        payload = { action: "roc", y_true: this.rawData?.[0] || [], y_score: this.rawData?.[1] || [] };
      }

      const result = await callJsonApi(endpoint, payload);
      this.resultsJson = result;
      this.results = JSON.stringify(result, null, 2);
      this.step = 3;
      this.viewMode = "raw";
      this.autoResult = null;
      this._storeToKB(result);
    } catch (e) {
      this.errorMessage = "Analysis failed: " + (e.message || "API unavailable");
    }
    this.loading = false;
  },

  async _storeToKB(result) {
    try {
      const at = this.activeAnalysis || this.testType;
      const summary = this.results ? this.results.substring(0, 1500) : JSON.stringify(result).substring(0, 1500);
      await callJsonApi("knowledge", {
        action: "store", category: "statistics",
        title: `Statistics: ${at} — ${this.fileName}`,
        content: `## Statistical Analysis: ${at}\n\n**File:** ${this.fileName}\n**Rows:** ${this.rowCount} | **Columns:** ${this.columns.length}\n\n\`\`\`json\n${summary}\n\`\`\``,
        tags: `${at},statistics,${this.fileName}`,
        source: "Statistics Module",
      });
    } catch (e) { /* silent */ }
  },

  // === Persistence ===
  persist() {
    try {
      localStorage.setItem("biodockify.statistics", JSON.stringify({
        fileName: this.fileName, columns: this.columns, rowCount: this.rowCount,
        testType: this.testType, selectedGroupCol: this.selectedGroupCol,
        selectedValueCol: this.selectedValueCol, correlationMethod: this.correlationMethod,
      }));
    } catch (e) {}
  },

  restore() {
    try {
      const s = JSON.parse(localStorage.getItem("biodockify.statistics") || "{}");
      if (s.fileName && s.columns?.length) {
        this.fileName = s.fileName; this.columns = s.columns;
        this.rowCount = s.rowCount || 0; this.hasData = true; this.step = 2;
      }
      if (s.testType) this.testType = s.testType;
      if (s.selectedGroupCol) this.selectedGroupCol = s.selectedGroupCol;
      if (s.selectedValueCol) this.selectedValueCol = s.selectedValueCol;
      if (s.correlationMethod) this.correlationMethod = s.correlationMethod;
    } catch (e) {}
  },

  // === Results helpers ===
  resetData() {
    this.step = 1; this.hasData = false; this.fileName = ""; this.columns = [];
    this.rowCount = 0; this.rawData = null; this.testType = null;
    this.selectedGroupCol = ""; this.selectedValueCol = ""; this.selectedCorrCols = [];
    this.results = ""; this.resultsJson = null; this.errorMessage = "";
    this.activeAnalysis = ""; this.viewMode = "auto"; this.autoResult = null;
  },

  downloadResults(format) {
    if (!this.resultsJson) return;
    let content, mime, ext;
    if (format === "csv") {
      const r = this.resultsJson?.results || this.resultsJson;
      content = "key,value\n" + Object.entries(r || {}).map(([k, v]) => `${k},${v}`).join("\n");
      mime = "text/csv"; ext = "csv";
    } else {
      content = JSON.stringify(this.resultsJson, null, 2);
      mime = "application/json"; ext = "json";
    }
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `statistics-results.${ext}`;
    a.click(); URL.revokeObjectURL(url);
  },

  saveToNotebook() {
    if (!this.resultsJson) return;
    const title = `${this.activeAnalysis || "Analysis"} on ${this.fileName || "data"}`;
    const content = typeof this.results === "string" ? this.results : JSON.stringify(this.resultsJson || {}, null, 2);
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry) {
      $store.knowledgeModal.addNoteBookEntry(title, content, "Statistical Analysis", ["statistics", this.activeAnalysis || "analysis"]);
    }
  },

  sendToAgent(prompt) {
    const input = document.getElementById("chat-input");
    if (input) { input.value = prompt; input.dispatchEvent(new Event("input", { bubbles: true })); input.focus(); }
  },

  closeModal() { this.resetData(); if (typeof closeModal === "function") closeModal(); },
}));
