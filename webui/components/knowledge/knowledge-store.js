import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("knowledgeModal", {
  entries: [],
  searchQuery: "",
  searchResults: [],
  newEntry: { question: "", answer: "" },
  loading: false,
  error: "",

  async search() {
    if (!this.searchQuery.trim()) return;
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("knowledge/query", {
        query: this.searchQuery,
        top_k: 5
      });
      this.searchResults = result.results || [];
    } catch (e) {
      this.error = e.message;
      this.searchResults = [];
    }
    this.loading = false;
  },

  addEntry() {
    if (!this.newEntry.question.trim()) return;
    this.entries.push({ ...this.newEntry, id: Date.now() });
    this.newEntry = { question: "", answer: "" };
  },

  deleteEntry(entry) {
    this.entries = this.entries.filter(e => e.id !== entry.id);
  },

  exportJson() {
    const data = JSON.stringify(this.entries, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "knowledge-base.json";
    a.click();
  }
});