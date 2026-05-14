import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("patentSearch", {
  query: "",
  loading: false,
  results: [],
  total: 0,
  message: "",
  error: "",

  async search() {
    if (!this.query.trim()) return;
    this.loading = true;
    this.error = "";
    this.message = "";
    try {
      const resp = await callJsonApi("patent_search", { query: this.query });
      if (resp.error) { this.error = resp.error; return; }
      this.results = resp.patents || [];
      this.total = resp.total || 0;
      this.message = resp.message || "";
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() { this.query = ""; this.results = []; this.total = 0; this.error = ""; this.message = ""; }
});
