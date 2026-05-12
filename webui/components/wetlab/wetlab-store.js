import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("wetlabModal", {
  experiments: [],
  newExperiment: { name: "", type: "", status: "planned" },
  loading: false,
  error: "",

  async loadExperiments() {
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("research/management/wetlab/pending", { research_id: "default" });
      this.experiments = result.experiments || [];
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  async addExperiment() {
    if (!this.newExperiment.name.trim()) return;
    this.loading = true;
    try {
      const result = await callJsonApi("research/management/wetlab/create", {
        name: this.newExperiment.name,
        type: this.newExperiment.type,
        status: "planned"
      });
      this.experiments.push({ ...this.newExperiment, id: Date.now(), date: new Date().toISOString() });
      this.newExperiment = { name: "", type: "", status: "planned" };
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  async updateStatus(exp, status) {
    try {
      await callJsonApi("research/management/wetlab/start/" + exp.id, {});
      exp.status = status;
    } catch (e) {
      exp.status = status;
    }
  },

  async deleteExperiment(exp) {
    this.experiments = this.experiments.filter(e => e.id !== exp.id);
  }
});