import { callJsonApi } from "/js/api.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("statisticsModal", () => ({
    // Step tracking
    step: 1,
    hasData: false,
    fileName: "",
    columns: [],
    selectedColumns: {},

    // Analysis
    results: "",
    loading: false,
    lastAnalysis: null,
    activeAnalysis: "",

    // Step 1: Upload data
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
          const result = await fetch("/api/statistics/import-data", {
            method: "POST",
            body: formData,
            headers: { "X-CSRF-Token": await getCsrfToken() }
          });
          const data = await result.json();
          this.columns = data.columns || data.column_names || [];
          this.hasData = true;
          this.step = 2;
          this.results = "Data loaded: " + (data.row_count || "?") + " rows, " + this.columns.length + " columns";
        } catch (e) {
          this.results = "Import error: " + e.message;
        }
        this.loading = false;
      };
      input.click();
    },

    // Step 2: Select & run analysis
    async runAnalysis(type) {
      this.activeAnalysis = type;
      this.loading = true;
      this.results = "";
      try {
        let payload = {};
        let endpoint = "";

        switch (type) {
          case "descriptive":
            endpoint = "statistics/analyze/descriptive";
            break;
          case "ttest":
            endpoint = "statistics/analyze/t-test";
            payload = {
              group_col: prompt("Group column name:"),
              value_col: prompt("Value column name:"),
              test_type: "independent",
              equal_var: true
            };
            if (!payload.group_col || !payload.value_col) { this.loading = false; return; }
            break;
          case "anova":
            endpoint = "statistics/analyze/anova";
            payload = {
              value_col: prompt("Value column name:"),
              group_col: prompt("Group column name:"),
              post_hoc: true
            };
            if (!payload.value_col || !payload.group_col) { this.loading = false; return; }
            break;
          case "correlation":
            endpoint = "statistics/analyze/correlation";
            const cols = prompt("Column names (comma-separated):");
            if (!cols) { this.loading = false; return; }
            payload = { columns: cols.split(",").map(c => c.trim()), method: "pearson" };
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
            payload = { test_type: "ttest_ind", effect_size: 0.5, alpha: 0.05, power: 0.80 };
            break;
          case "pkpd":
            this.results = "PK/PD Analysis: Provide concentration/time data via the agent chat";
            this.loading = false;
            return;
        }

        if (endpoint) {
          const result = await callJsonApi(endpoint, payload);
          this.results = JSON.stringify(result, null, 2);
          this.lastAnalysis = result;
        }
        this.step = 3;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    resetData() {
      this.hasData = false;
      this.step = 1;
      this.fileName = "";
      this.columns = [];
      this.selectedColumns = {};
      this.results = "";
      this.lastAnalysis = null;
    },

    closeModal() {
      this.resetData();
      closeTopModal();
    }
  }));
});

async function getCsrfToken() {
  const resp = await fetch("/api/csrf_token");
  const json = await resp.json();
  return json.token;
}
