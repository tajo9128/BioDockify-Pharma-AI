import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("knowledgeModal", {
  entries: [],
  searchQuery: "",
  searchResults: [],
  newEntry: { question: "", answer: "" },
  loading: false,
  uploading: false,
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
  },

  triggerFileUpload() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.pdf,.txt,.md,.json,.docx";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = e.target.files;
      if (!files || !files.length) return;
      this.uploading = true;
      this.error = "";
      try {
        const formData = new FormData();
        for (const file of files) {
          formData.append("files", file);
        }
        const resp = await fetch("/api/knowledge/import", {
          method: "POST",
          body: formData,
          headers: { "X-CSRF-Token": await getCsrfToken() }
        });
        const result = await resp.json();
        if (result.success) {
          this.entries.push({
            id: Date.now(),
            question: `Imported: ${files.length} file(s)`,
            answer: `${result.count || files.length} document(s) added to knowledge base`
          });
        } else {
          this.error = result.error || "Import failed";
        }
      } catch (e) {
        this.error = "Upload error: " + e.message;
      }
      this.uploading = false;
    };
    input.click();
  }
});

async function getCsrfToken() {
  try {
    const resp = await fetch("/api/csrf_token");
    const json = await resp.json();
    return json.token;
  } catch { return ""; }
}