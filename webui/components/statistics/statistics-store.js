import { callJsonApi } from "/js/api.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("statisticsModal", () => ({
    step: 1,
    hasData: false,
    fileName: "",
    columns: [],
    rowCount: 0,

    // Form state
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

    get columnOptions() {
      return this.columns.map(c => ({ value: c, label: c }));
    },

    selectTest(type) {
      this.testType = type;
      this.results = "";
      this.resultsJson = null;
    },

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
            method: "POST",
            body: formData,
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
          } else {
            this.results = "Import failed: " + (data.detail || data.error || "Unknown error");
          }
        } catch (e) {
          this.results = "Import error: " + e.message;
        }
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
          case "descriptive":
            endpoint = "statistics/analyze/descriptive";
            break;
          case "correlation":
            if (this.selectedCorrCols.length < 2) {
              this.results = "Please select at least 2 columns for correlation";
              this.loading = false;
              return;
            }
            endpoint = "statistics/analyze/correlation";
            payload = {
              columns: this.selectedCorrCols,
              method: this.correlationMethod
            };
            break;
          case "ttest":
            if (!this.selectedGroupCol || !this.selectedValueCol) {
              this.results = "Please select both Group and Value columns";
              this.loading = false;
              return;
            }
            endpoint = "statistics/analyze/t-test";
            payload = {
              group_col: this.selectedGroupCol,
              value_col: this.selectedValueCol,
              test_type: this.ttestType,
              equal_var: this.ttestEqualVar
            };
            break;
          case "anova":
            if (!this.selectedGroupCol || !this.selectedValueCol) {
              this.results = "Please select both Group and Value columns";
              this.loading = false;
              return;
            }
            endpoint = "statistics/analyze/anova";
            payload = {
              group_col: this.selectedGroupCol,
              value_col: this.selectedValueCol,
              post_hoc: this.anovaPostHoc
            };
            break;
          case "regression":
            this.results = "Regression: Provide X/Y columns via the agent chat";
            this.loading = false;
            return;
          case "survival":
            this.results = "Survival Analysis: Provide time_col, event_col via the agent chat";
            this.loading = false;
            return;
          case "power":
            endpoint = "statistics/analyze/power";
            payload = {
              test_type: "ttest_ind",
              effect_size: this.powerEffectSize,
              alpha: this.powerAlpha,
              power: this.powerTarget
            };
            break;
          case "pkpd":
            this.results = "PK/PD Analysis: Provide concentration/time data via the agent chat";
            this.loading = false;
            return;
          default:
            this.results = "Unknown analysis type";
            this.loading = false;
            return;
        }

        if (endpoint) {
          const result = await callJsonApi(endpoint, payload);
          this.resultsJson = result;
          this.results = JSON.stringify(result, null, 2);
          this.step = 3;
        }
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    formatTable(json) {
      if (!json) return "";
      try {
        const data = typeof json === "string" ? JSON.parse(json) : json;
        if (data.status === "success" && data.results) {
          const r = data.results;
          if (r.descriptive_statistics) {
            return this._buildDescTable(r.descriptive_statistics);
          }
          if (r.correlation_matrix) {
            return this._buildCorrTable(r.correlation_matrix);
          }
          if (r.ttest_results || r.anova_results) {
            return this._buildTestTable(r.ttest_results || r.anova_results || r);
          }
          return this._buildGenericTable(r);
        }
        if (Array.isArray(data)) {
          return this._buildGenericTable(data);
        }
        return this._buildGenericTable(data);
      } catch {
        return "";
      }
    },

    _buildDescTable(stats) {
      let html = '<table><thead><tr><th>Column</th><th>Mean</th><th>StdDev</th><th>Min</th><th>Max</th><th>N</th></tr></thead><tbody>';
      for (const [col, vals] of Object.entries(stats)) {
        if (typeof vals === "object") {
          html += `<tr><td>${col}</td><td>${(vals.mean||0).toFixed(4)}</td><td>${(vals.std||0).toFixed(4)}</td><td>${vals.min||""}</td><td>${vals.max||""}</td><td>${vals.count||""}</td></tr>`;
        }
      }
      html += '</tbody></table>';
      return html;
    },

    _buildCorrTable(matrix) {
      if (!Array.isArray(matrix) || !matrix.length) return "";
      const cols = Object.keys(matrix[0] || {});
      let html = '<table><thead><tr><th></th>';
      cols.forEach(c => { html += `<th>${c}</th>`; });
      html += '</tr></thead><tbody>';
      matrix.forEach((row, i) => {
        html += `<tr><td><strong>${cols[i]||''}</strong></td>`;
        cols.forEach(c => { html += `<td>${(row[c]||0).toFixed(3)}</td>`; });
        html += '</tr>';
      });
      html += '</tbody></table>';
      return html;
    },

    _buildTestTable(result) {
      let html = '<table><thead><tr>';
      const keys = Object.keys(result);
      keys.forEach(k => { html += `<th>${k}</th>`; });
      html += '</tr></thead><tbody><tr>';
      keys.forEach(k => { html += `<td>${typeof result[k]==='number' ? result[k].toFixed(4) : result[k]}</td>`; });
      html += '</tr></tbody></table>';
      return html;
    },

    _buildGenericTable(data) {
      if (!data) return "";
      let html = '<table><thead><tr>';
      const keys = Object.keys(data);
      keys.forEach(k => { html += `<th>${k}</th>`; });
      html += '</tr></thead><tbody><tr>';
      keys.forEach(k => {
        const v = data[k];
        html += `<td>${typeof v === 'number' ? v.toFixed(4) : String(v)}</td>`;
      });
      html += '</tr></tbody></table>';
      return html;
    },

    downloadResults(format) {
      if (!this.resultsJson && !this.results) return;
      const data = this.resultsJson || (typeof this.results === "string" ? JSON.parse(this.results) : this.results);
      let content, mime, ext;

      if (format === "csv") {
        content = this._toCSV(data);
        mime = "text/csv";
        ext = "csv";
      } else if (format === "json") {
        content = JSON.stringify(data, null, 2);
        mime = "application/json";
        ext = "json";
      } else {
        content = JSON.stringify(data, null, 2);
        mime = "application/json";
        ext = "json";
      }

      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `statistics-results.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    },

    _toCSV(data) {
      if (!data) return "";
      const results = data.results || data;
      if (results.descriptive_statistics) {
        let csv = "Column,Mean,StdDev,Min,Max,Count\n";
        for (const [col, vals] of Object.entries(results.descriptive_statistics)) {
          if (typeof vals === "object") {
            csv += `${col},${vals.mean||""},${vals.std||""},${vals.min||""},${vals.max||""},${vals.count||""}\n`;
          }
        }
        return csv;
      }
      if (results.correlation_matrix && Array.isArray(results.correlation_matrix)) {
        const cols = Object.keys(results.correlation_matrix[0] || {});
        let csv = "," + cols.join(",") + "\n";
        results.correlation_matrix.forEach((row, i) => {
          csv += (cols[i]||"") + "," + cols.map(c => row[c]||"").join(",") + "\n";
        });
        return csv;
      }
      const keys = Object.keys(results);
      return keys.join(",") + "\n" + keys.map(k => results[k]).join(",") + "\n";
    },

    copyResults() {
      if (!this.results) return;
      navigator.clipboard.writeText(this.results).then(() => {
        this.results = "[Copied!]\n" + this.results;
        setTimeout(() => {
          this.results = this.results.replace("[Copied!]\n", "");
        }, 1500);
      });
    },

    resetData() {
      this.hasData = false;
      this.step = 1;
      this.fileName = "";
      this.columns = [];
      this.rowCount = 0;
      this.selectedGroupCol = "";
      this.selectedValueCol = "";
      this.selectedCorrCols = [];
      this.testType = null;
      this.results = "";
      this.resultsJson = null;
      this.activeAnalysis = "";
      this.viewMode = "table";
    },

    closeModal() {
      this.resetData();
      closeTopModal();
    },

    sendToAgent(prompt) {
      if (typeof showToast === "function") {
        showToast("Sent to agent chat: " + prompt.substring(0, 80) + "...");
      }
      const input = document.querySelector("#chat-bar-input textarea, .chat-bar-input textarea, .input-area textarea");
      if (input) {
        input.value = prompt;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
      }
    },

    handleDrop(event) {
      // reuse importData for drag-and-drop
      const file = event.dataTransfer?.files?.[0];
      if (!file) return;
      this.loading = true;
      this.fileName = file.name;
      const formData = new FormData();
      formData.append("file", file);
      fetch("/api/statistics/import-data", {
        method: "POST",
        body: formData,
        headers: { "X-CSRF-Token": getCsrfToken() }
      }).then(r => r.json()).then(data => {
        if (data.status === "success" || data.data_summary) {
          const s = data.data_summary || data;
          this.columns = s.column_names || [];
          this.rowCount = s.rows || 0;
          this.hasData = true;
          this.step = 2;
        } else {
          this.results = "Import failed: " + (data.detail || "Unknown error");
        }
      }).catch(e => {
        this.results = "Import error: " + e.message;
      }).finally(() => { this.loading = false; });
    }
  }));
});

async function getCsrfToken() {
  const resp = await fetch("/api/csrf_token");
  const json = await resp.json();
  return json.token;
}
