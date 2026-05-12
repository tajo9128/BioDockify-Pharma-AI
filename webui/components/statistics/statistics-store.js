import { callJsonApi } from "/js/api.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("statisticsModal", () => ({
    results: "",
    loading: false,
    lastAnalysis: null,

    async runDescriptive() {
      this.loading = true;
      try {
        const result = await callJsonApi("statistics/analyze/descriptive", {});
        this.results = JSON.stringify(result, null, 2);
        this.lastAnalysis = result;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    async runTTest() {
      this.loading = true;
      try {
        const groupCol = prompt("Group column name (e.g., 'Group'):");
        if (!groupCol) { this.loading = false; return; }
        const valueCol = prompt("Value column name (e.g., 'Result'):");
        if (!valueCol) { this.loading = false; return; }
        const result = await callJsonApi("statistics/analyze/t-test", {
          group_col: groupCol,
          value_col: valueCol,
          test_type: "independent",
          equal_var: true
        });
        this.results = JSON.stringify(result, null, 2);
        this.lastAnalysis = result;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    async runAnova() {
      this.loading = true;
      try {
        const valueCol = prompt("Value column name (e.g., 'Score'):");
        if (!valueCol) { this.loading = false; return; }
        const groupCol = prompt("Group column name (e.g., 'Treatment'):");
        if (!groupCol) { this.loading = false; return; }
        const result = await callJsonApi("statistics/analyze/anova", {
          value_col: valueCol,
          group_col: groupCol,
          post_hoc: true
        });
        this.results = JSON.stringify(result, null, 2);
        this.lastAnalysis = result;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    async runCorrelation() {
      this.loading = true;
      try {
        const cols = prompt("Comma-separated column names for correlation:");
        if (!cols) { this.loading = false; return; }
        const columns = cols.split(",").map(c => c.trim());
        const result = await callJsonApi("statistics/analyze/correlation", {
          columns: columns,
          method: "pearson"
        });
        this.results = JSON.stringify(result, null, 2);
        this.lastAnalysis = result;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    async runRegression() {
      this.results = "Regression: Use the agent chat to provide X/Y columns and specify regression type";
    },

    async runSurvival() {
      this.results = "Survival Analysis: Use the agent chat with time_col, event_col, and covariates";
    },

    async runPower() {
      this.loading = true;
      try {
        const result = await callJsonApi("statistics/analyze/power", {
          test_type: "ttest_ind",
          effect_size: 0.5,
          alpha: 0.05,
          power: 0.80
        });
        this.results = JSON.stringify(result, null, 2);
        this.lastAnalysis = result;
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    async runPKPD() {
      this.results = "PK/PD Analysis: Use the agent chat with time/concentration data for NCA or compartmental modeling";
    },

    async importData() {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".csv,.xlsx,.xls,.json";
      input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        this.loading = true;
        try {
          const formData = new FormData();
          formData.append("file", file);
          const result = await fetch("/api/statistics/import-data", {
            method: "POST",
            body: formData,
            headers: { "X-CSRF-Token": await getCsrfToken() }
          });
          const data = await result.json();
          this.results = "Data imported:\n" + JSON.stringify(data, null, 2);
        } catch (e) {
          this.results = "Import error: " + e.message;
        }
        this.loading = false;
      };
      input.click();
    },

    async getAvailableAnalyses() {
      this.loading = true;
      try {
        const result = await callJsonApi("statistics/available-analyses", {});
        this.results = JSON.stringify(result, null, 2);
      } catch (e) {
        this.results = "Error: " + e.message;
      }
      this.loading = false;
    },

    closeModal() {
      this.results = "";
      this.lastAnalysis = null;
      closeTopModal();
    },
  }));
});

async function getCsrfToken() {
  const resp = await fetch("/api/csrf_token");
  const json = await resp.json();
  return json.token;
}