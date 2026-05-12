import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("literatureModal", {
  query: "",
  selectedDb: "pubmed",
  results: [],
  loading: false,
  error: "",

  async searchLiterature() {
    if (!this.query.trim()) return;
    this.loading = true;
    this.error = "";
    try {
      const response = await callJsonApi("literature/search", {
        query: this.query,
        limit: 15,
        sources: this.selectedDb === "all" ? null : [this.selectedDb]
      });
      this.results = response.papers || [];
    } catch (e) {
      this.error = e.message;
      this.results = [];
    }
    this.loading = false;
  },

  async synthesizePapers() {
    if (this.results.length === 0) {
      this.error = "No papers to synthesize. Search first.";
      return;
    }
    this.loading = true;
    try {
      const response = await callJsonApi("literature/synthesize", {
        topic: this.query,
        papers: this.results
      });
      return response.review || "Synthesis complete.";
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  }
});