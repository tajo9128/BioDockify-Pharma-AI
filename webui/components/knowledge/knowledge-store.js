import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, getCsrfToken } from "/js/api.js";

const LS_KEY = "biodockify.notebook";

export const store = createStore("knowledgeModal", {
  activeTab: "notebook",
  entries: [],
  searchQuery: "",
  searchResults: [],
  newEntry: { question: "", answer: "", tags: [], source: "" },
  loading: false,
  uploading: false,
  error: "",
  message: "",
  // Chat
  chatMessages: [],
  chatInput: "",
  chatLoading: false,
  // Library
  libraryCategories: [],

  // Tags
  tags: ["biochemistry", "pharmacology", "molecular-biology", "medicinal-chemistry", "drug-discovery"],
  activeTag: null,
  favorites: [],
  viewMode: "list",

  // Graph
  showGraph: false,
  graphData: { nodes: [], edges: [] },

  _restored: false,

  persist() {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        entries: this.entries.filter(e => e.saved),
        tags: this.tags,
        favorites: this.favorites,
      }));
    } catch {}
  },

  restore() {
    if (this._restored) return;
    this._restored = true;
    try {
      const s = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
      if (s.entries) this.entries = s.entries;
      if (s.tags) this.tags = s.tags;
      if (s.favorites) this.favorites = s.favorites;
    } catch {}
  },

  get filteredEntries() {
    if (this.activeTag) {
      return this.entries.filter(e => (e.tags || []).includes(this.activeTag));
    }
    return this.entries;
  },

  get favoriteEntries() {
    return this.entries.filter(e => this.favorites.includes(e.id));
  },

  get entryCount() { return this.entries.length; },

  async search() {
    if (!this.searchQuery.trim()) return;
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("knowledge", {
        action: "query",
        query: this.searchQuery,
        top_k: 10
      });
      this.searchResults = result.results || [];
      if (!this.searchResults.length) {
        this.message = "No results found. Try different keywords or upload documents first.";
        setTimeout(() => { this.message = ""; }, 3000);
      }
    } catch (e) {
      this.error = e.message;
      this.searchResults = [];
    }
    this.loading = false;
  },

  addEntry() {
    if (!this.newEntry.question.trim()) return;
    const entry = {
      id: Date.now(),
      question: this.newEntry.question,
      answer: this.newEntry.answer,
      tags: this.newEntry.tags || [],
      source: this.newEntry.source || "",
      saved: false,
      createdAt: new Date().toISOString(),
    };
    this.entries.unshift(entry);
    this.newEntry = { question: "", answer: "", tags: [], source: "" };
    this.persist();
  },

  addNoteBookEntry(title, content, source, tags) {
    if (!title) return;
    this.entries.unshift({
      id: Date.now(),
      question: title,
      answer: content || "",
      tags: tags || [],
      source: source || "",
      saved: true,
      createdAt: new Date().toISOString(),
    });
    this.persist();
    this.message = "Entry saved to notebook";
    setTimeout(() => { this.message = ""; }, 2000);
  },

  toggleFavorite(id) {
    const idx = this.favorites.indexOf(id);
    if (idx >= 0) { this.favorites.splice(idx, 1); }
    else { this.favorites.push(id); }
    const entry = this.entries.find(e => e.id === id);
    if (entry) {
      entry.saved = !entry.saved;
      this.persist();
    }
  },

  deleteEntry(entry) {
    this.entries = this.entries.filter(e => e.id !== entry.id);
    this.favorites = this.favorites.filter(id => id !== entry.id);
    this.persist();
  },

  addTag(tag) {
    tag = tag.trim().toLowerCase().replace(/\s+/g, "-");
    if (tag && !this.tags.includes(tag)) {
      this.tags.push(tag);
      this.persist();
    }
  },

  filterByTag(tag) {
    this.activeTag = this.activeTag === tag ? null : tag;
  },

  buildGraph() {
    const nodes = [];
    const edges = [];
    const nodeMap = {};

    this.entries.forEach(entry => {
      const nodeId = "e" + entry.id;
      if (!nodeMap[nodeId]) {
        nodes.push({ id: nodeId, label: (entry.question || "").substring(0, 30), type: "entry" });
        nodeMap[nodeId] = true;
      }
      (entry.tags || []).forEach(tag => {
        const tagId = "t" + tag;
        if (!nodeMap[tagId]) {
          nodes.push({ id: tagId, label: tag, type: "tag" });
          nodeMap[tagId] = true;
        }
        edges.push({ source: nodeId, target: tagId });
      });
      if (entry.source) {
        const srcId = "s" + entry.source.substring(0, 20);
        if (!nodeMap[srcId]) {
          nodes.push({ id: srcId, label: entry.source.substring(0, 25), type: "source" });
          nodeMap[srcId] = true;
        }
        edges.push({ source: nodeId, target: srcId });
      }
    });

    this.graphData = { nodes, edges };
    this.showGraph = true;
  },

  chatWithKB() {
    this.activeTab = "chat";
    if (!this.chatMessages.length && this.entries.length) {
      const ctx = this.entries.slice(0, 30).map(e => `${e.question}: ${e.answer}`).join("\n").substring(0, 4000);
      this.chatMessages = [{ role: "system", content: `Knowledge base:\n${ctx}` }];
    }
  },

  async sendMessage() {
    if (!this.chatInput.trim()) return;
    const msg = this.chatInput.trim();
    this.chatMessages.push({ role: "user", content: msg });
    this.chatInput = "";
    this.chatLoading = true;
    try {
      const ctx = this.entries.slice(0, 30).map(e => `${e.question}: ${e.answer}`).join("\n").substring(0, 4000);
      const prompt = `Based on this knowledge base:\n${ctx}\n\nAnswer: ${msg}`;
      const input = document.getElementById("chat-input") || document.querySelector("textarea[data-chat-input]");
      if (input) { input.value = prompt; input.dispatchEvent(new Event("input", { bubbles: true })); input.focus(); }
      this.chatMessages.push({ role: "assistant", content: "Sent to Agent Zero. Check the chat panel for the response." });
    } catch (e) { this.chatMessages.push({ role: "assistant", content: "Error: " + e.message }); }
    this.chatLoading = false;
  },

  buildLibrary() {
    const cats = {};
    for (const entry of this.entries) {
      for (const tag of (entry.tags || ["untagged"])) {
        if (!cats[tag]) cats[tag] = { name: tag, count: 0, items: [] };
        cats[tag].count++;
        if (cats[tag].items.length < 5) cats[tag].items.push(entry.question);
      }
    }
    this.libraryCategories = Object.values(cats).sort((a, b) => b.count - a.count);
  },

  openInWriter(entry) {
    if (typeof $store !== "undefined" && $store.desktopWorkspace) {
      $store.desktopWorkspace.openWindow("thesis");
    }
    setTimeout(() => {
      const input = document.querySelector(".aw-topic-input");
      if (input) {
        input.value = entry.question || "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }, 400);
  },

  async addFromLiterature(paper) {
    this.addNoteBookEntry(
      paper.title,
      paper.abstract || "",
      paper.journal || paper.database || "Literature",
      ["literature", "paper"]
    );
  },

  exportJson() {
    const data = JSON.stringify(this.entries, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "research-notebook.json";
    a.click();
    URL.revokeObjectURL(url);
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
        const fileData = [];
        for (const file of files) {
          const text = await file.text();
          fileData.push({ filename: file.name, content: text });
        }
        const result = await callJsonApi("knowledge", {
          action: "import_files",
          files: fileData,
        });
        if (result.success) {
          this.addNoteBookEntry(
            `Uploaded: ${files.length} file(s)`,
            `${result.count || files.length} document(s) added to knowledge base`,
            "File Upload",
            ["upload", "import"]
          );
        } else {
          this.error = result.error || "Import failed";
        }
      } catch (e) {
        this.error = "Upload error: " + e.message;
      }
      this.uploading = false;
    };
    input.click();
  },

  async reindexKB() {
    this.loading = true;
    this.error = "";
    try {
      const r = await callJsonApi("knowledge", { action: "reindex" });
      if (r.status === "ok") {
        this.message = r.message || "Re-indexed successfully";
      } else {
        this.error = r.error || "Re-index failed";
      }
    } catch (e) {
      this.error = "Re-index error: " + e.message;
    }
    this.loading = false;
    setTimeout(() => { this.message = ""; }, 5000);
  },

  async loadKBStatus() {
    try {
      const r = await callJsonApi("knowledge", { action: "status" });
      if (r.status === "ok") {
        this.kbStatus = r;
      }
    } catch (e) {}
  },
});


