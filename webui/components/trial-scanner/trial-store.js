import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("trialSearch", {
  query: "",
  condition: "",
  status: "",
  loading: false,
  results: [],
  total: 0,
  error: "",
  message: "",

  async search() {
    if (!this.query.trim() && !this.condition.trim()) return;
    this.loading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("trial_search", {
        query: this.query,
        condition: this.condition,
        status: this.status
      });
      if (resp.error) { this.error = resp.error; return; }
      this.results = resp.trials || [];
      this.total = resp.total || 0;
      this.message = resp.message || "";
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() { this.query = ""; this.condition = ""; this.status = ""; this.results = []; this.total = 0; this.error = ""; this.message = ""; }
});
