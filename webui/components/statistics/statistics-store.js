import { callJsonApi } from "/js/api.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("statisticsModal", () => ({
    results: "",

    async runDescriptive() {
      try {
        const data = prompt("Enter comma-separated numbers:");
        if (!data) return;
        const numbers = data.split(",").map((n) => parseFloat(n.trim())).filter((n) => !isNaN(n));
        const result = await callJsonApi("statistics/analyze", {
          method: "descriptive_stats",
          data: numbers,
        });
        this.results = JSON.stringify(result, null, 2);
      } catch (e) {
        this.results = "Error: " + e.message;
      }
    },

    async runTTest() {
      try {
        const g1 = prompt("Group 1 (comma-separated numbers):");
        if (!g1) return;
        const g2 = prompt("Group 2 (comma-separated numbers):");
        if (!g2) return;
        const result = await callJsonApi("statistics/analyze/two-sample-t-test", {
          group1: g1.split(",").map((n) => parseFloat(n.trim())),
          group2: g2.split(",").map((n) => parseFloat(n.trim())),
        });
        this.results = JSON.stringify(result, null, 2);
      } catch (e) {
        this.results = "Error: " + e.message;
      }
    },

    async runAnova() {
      this.results = "ANOVA: Select groups to compare via agent chat";
    },

    async runCorrelation() {
      this.results = "Correlation: Send data via agent for analysis";
    },

    async runRegression() {
      this.results = "Regression: Send data via agent for analysis";
    },

    async runSurvival() {
      this.results = "Survival: Send data via agent for analysis";
    },

    async runPower() {
      this.results = "Power Analysis: Send requirements via agent";
    },

    async runPKPD() {
      this.results = "PK/PD Analysis: Send data via agent";
    },

    closeModal() {
      this.results = "";
      closeTopModal();
    },
  }));
});