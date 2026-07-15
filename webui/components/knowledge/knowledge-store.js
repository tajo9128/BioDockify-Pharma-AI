import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, getCsrfToken } from "/js/api.js";

const LS_KEY = "biodockify.notebook";

export const store = createStore("knowledgeModal", {
  activeTab: "all",
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
  libraryEntries: [],
  libraryCategory: "",
  kbStatus: null,

  // Tags
  tags: ["biochemistry", "pharmacology", "molecular-biology", "medicinal-chemistry", "drug-discovery"],
  activeTag: null,
  favorites: [],
  selected: {},   // {entryId: true}
  viewMode: "list",

  // Graph
  showGraph: false,
  graphData: { nodes: [], edges: [] },

  // Document card view (Google NotebookLM style)
  expandedEntry: null,
  docCardView: true,
  readingPaper: null,  // Full-paper reader state

  // Podcast
  podcastText: "",
  podcastVoice: "alloy",
  podcastUrl: "",
  podcastLoading: false,

  // Category management + file selection (WordPress-style)
  customCategories: [],
  activeCategory: "all",  // "all" or a category key
  selectedIds: [],        // checked file IDs
  showAddCategory: false,
  newCategoryName: "",

  _restored: false,

  // Detect if an entry contains a paper/document collection
  isPaperCollection(entry) {
    return entry?.tags?.includes("literature") || entry?.tags?.includes("paper") || entry?.tags?.includes("deep_research");
  },

  // Parse papers from an entry's answer content (JSON array of papers)
  parsePapers(entry) {
    if (!entry?.answer) return [];
    try {
      const parsed = JSON.parse(entry.answer);
      if (Array.isArray(parsed)) return parsed;
      if (parsed?.papers && Array.isArray(parsed.papers)) return parsed.papers;
      if (parsed?.results && Array.isArray(parsed.results)) return parsed.results;
      return [];
    } catch { return []; }
  },

  // Try parsing papers but catch errors silently
  tryParsePapers(answer) {
    if (!answer) return { papers: [], isCollection: false };
    try {
      const parsed = JSON.parse(answer);
      if (Array.isArray(parsed)) return { papers: parsed, isCollection: true };
      if (parsed?.papers) return { papers: parsed.papers, isCollection: true };
      if (parsed?.results) return { papers: parsed.results, isCollection: true };
      if (parsed?.title || parsed?.authors) return { papers: [parsed], isCollection: true };
      return { papers: [], isCollection: false };
    } catch { return { papers: [], isCollection: false }; }
  },

  // Format authors list
  formatAuthors(authors) {
    if (!authors) return "";
    if (Array.isArray(authors)) return authors.slice(0, 3).join(", ") + (authors.length > 3 ? " et al." : "");
    return String(authors);
  },

  // Full-paper reader
  openPaperReader(paper) {
    this.readingPaper = paper;
  },

  closePaperReader() {
    this.readingPaper = null;
  },

  // Get full text content from paper object (checks multiple field names)
  getFullText(paper) {
    return paper?.full_text || paper?.content || paper?.text || paper?.body || paper?.answer || "";
  },

  // Get all metadata fields from paper
  getPaperMetadata(paper) {
    const meta = [];
    if (paper?.journal) meta.push({ label: "Journal", value: paper.journal });
    if (paper?.year) meta.push({ label: "Year", value: paper.year });
    if (paper?.doi) meta.push({ label: "DOI", value: paper.doi });
    if (paper?.url) meta.push({ label: "URL", value: paper.url });
    if (paper?.database) meta.push({ label: "Database", value: paper.database });
    if (paper?.citations) meta.push({ label: "Citations", value: paper.citations });
    if (paper?.keywords && paper.keywords.length) meta.push({ label: "Keywords", value: Array.isArray(paper.keywords) ? paper.keywords.join(", ") : paper.keywords });
    return meta;
  },

  async generatePodcast() {
    if (!this.podcastText.trim()) return;
    this.podcastLoading = true; this.podcastUrl = ""; this.error = "";
    try {
      const r = await callJsonApi("knowledge/podcast", {
        text: this.podcastText,
        voice: this.podcastVoice,
      });
      if (r.audio_base64) {
        const byteStr = atob(r.audio_base64);
        const bytes = new Uint8Array(byteStr.length);
        for (let i = 0; i < byteStr.length; i++) bytes[i] = byteStr.charCodeAt(i);
        const blob = new Blob([bytes], { type: "audio/mp3" });
        this.podcastUrl = URL.createObjectURL(blob);
        this.message = "Podcast generated";
      } else if (r.status === "success") {
        this.message = "Podcast generated";
      } else {
        this.error = r.error || "Podcast generation failed — check TTS API key in Settings";
      }
    } catch (e) { this.error = "Podcast error: " + e.message; }
    this.podcastLoading = false;
  },

  async addQuickNote() {
    const titleEl = document.getElementById("nb-note-title");
    const contentEl = document.getElementById("nb-note-content");
    const title = titleEl?.value?.trim();
    const content = contentEl?.value?.trim();
    if (!title || !content) return;
    try {
      await callJsonApi("knowledge", {
        action: "store",
        category: "notes",
        title: title,
        content: content,
        tags: "notes,knowledge-base",
        source: "Quick Note",
      });
      this.message = "Note saved to Knowledge Base";
      setTimeout(() => { this.message = ""; }, 2000);
      if (titleEl) titleEl.value = "";
      if (contentEl) contentEl.value = "";
    } catch (e) { this.error = "Save failed: " + e.message; }
  },

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
    // Load ALL KB entries immediately (no search required)
    this.loadAllEntries();
    this.loadLibraryFromKB();
  },

  get filteredEntries() {
    if (this.activeTag) {
      return this.entries.filter(e => (e.tags || []).includes(this.activeTag));
    }
    return this.entries;
  },

  async loadAllEntries() {
    /** Load ALL KB entries on open — no search required. */
    this.loading = true;
    try {
      const r = await callJsonApi("knowledge", { action: "list_all" });
      if (r.status === "ok" && r.entries) {
        // Merge: KB entries become the primary entries list
        const kbEntries = r.entries.map(e => ({
          id: e.id || Date.now(),
          question: e.title || "Untitled",
          answer: e.preview || "",  // Store preview as initial answer
          tags: e.tags || [e.category || "uncategorized"],
          source: e.source || e.category_label || "Knowledge Base",
          saved: true,
          createdAt: e.created_at || new Date().toISOString(),
          file: e.file || "",
          hasContent: e.has_content || false,
          contentLength: e.content_length || 0,
          _fullyLoaded: false,  // content not fully loaded yet
        }));

        // Keep local-only entries (notes created in UI but not in KB)
        const localOnly = this.entries.filter(e => !e.saved);
        // Combine: KB entries + local entries, dedupe by question title
        const all = [...kbEntries];
        for (const le of localOnly) {
          if (!all.find(a => a.question === le.question)) {
            all.unshift(le);
          }
        }

        this.entries = all;
        this.persist();
      }
    } catch (e) {
      console.error("loadAllEntries failed:", e);
    }
    this.loading = false;
  },

  async readEntry(entry) {
    /** Read full content of an entry from KB. Opens it in the reader. */
    if (entry._fullyLoaded) {
      this.readingPaper = entry;
      return;
    }
    this.loading = true;
    try {
      const r = await callJsonApi("knowledge", {
        action: "read_entry",
        file: entry.file || "",
        entry_id: typeof entry.id === "string" ? entry.id : "",
      });
      if (r.status === "ok" && r.content) {
        // Update the entry with full content
        const idx = this.entries.findIndex(e => e.id === entry.id);
        if (idx >= 0) {
          this.entries[idx].answer = r.content;
          this.entries[idx]._fullyLoaded = true;
        }
        // Open in reader view
        this.readingPaper = {
          ...entry,
          full_text: r.content,
          answer: r.content,
        };
      } else {
        // Fallback: show whatever content we have
        this.readingPaper = entry;
      }
    } catch (e) {
      this.error = "Failed to read entry: " + e.message;
    }
    this.loading = false;
  },

  get recentEntries() {
    return [...this.entries]
      .filter(e => e.createdAt || e.id)
      .sort((a, b) => {
        const da = a.createdAt || new Date(a.id || 0).toISOString();
        const db = b.createdAt || new Date(b.id || 0).toISOString();
        return db.localeCompare(da);
      })
      .slice(0, 50);
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
    // Call API to delete from KB filesystem if it's a KB entry
    if (entry.saved && (entry.file || entry.id)) {
      callJsonApi("knowledge", {
        action: "delete_entry",
        id: entry.id,
      }).catch(() => {});
    }
    this.entries = this.entries.filter(e => e.id !== entry.id);
    this.favorites = this.favorites.filter(id => id !== entry.id);
    delete this.selected[entry.id];
    this.persist();
  },

  toggleSelect(entry) {
    this.selected[entry.id] = !this.selected[entry.id];
  },

  get selectedCount() {
    return Object.values(this.selected).filter(Boolean).length;
  },

  deleteSelected() {
    const ids = Object.keys(this.selected).filter(k => this.selected[k]);
    for (const id of ids) {
      const entry = this.entries.find(e => e.id === id || e.id == id);
      if (entry) this.deleteEntry(entry);
    }
  },

  selectAll() {
    const allSelected = this.filteredEntries.every(e => this.selected[e.id]);
    for (const e of this.filteredEntries) {
      this.selected[e.id] = !allSelected;
    }
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
    // Build from local entries
    const cats = {};
    for (const entry of this.entries) {
      for (const tag of (entry.tags || ["untagged"])) {
        if (!cats[tag]) cats[tag] = { name: tag, count: 0, items: [] };
        cats[tag].count++;
        if (cats[tag].items.length < 5) cats[tag].items.push(entry.question);
      }
    }
    this.libraryCategories = Object.values(cats).sort((a, b) => b.count - a.count);
    // Also load from KB API
    this.loadLibraryFromKB();
  },

  async loadLibraryFromKB() {
    try {
      const r = await callJsonApi("knowledge", { action: "status" });
      if (r.status === "ok") {
        this.kbStatus = r;
        // Build categories from KB
        const kbCats = [];
        const labels = r.category_labels || {};
        for (const [key, count] of Object.entries(r.categories || {})) {
          kbCats.push({ name: key, label: labels[key] || key, count: count, source: "kb" });
        }
        // Merge with local categories
        for (const cat of kbCats) {
          const existing = this.libraryCategories.find(c => c.name === cat.name);
          if (existing) {
            existing.count += cat.count;
            existing.source = "kb";
            existing.label = cat.label;
          } else {
            this.libraryCategories.push(cat);
          }
        }
        this.libraryCategories.sort((a, b) => b.count - a.count);
      }
    } catch (e) {}
  },

  async loadLibraryEntries(category) {
    this.libraryCategory = category;
    this.loading = true;
    try {
      const r = await callJsonApi("knowledge", { action: "library", category: category, limit: 50 });
      if (r.status === "ok") {
        this.libraryEntries = r.entries || [];
      }
    } catch (e) {}
    this.loading = false;
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
    input.accept = ".csv,.pdf,.txt,.md,.json,.docx,.xlsx,.xls,.html,.htm,.sdf,.mol,.pdb,.pdbqt,.mp3,.wav,.mp4,.avi";
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
        // Use 'upload' action — auto-detects category from file type
        const result = await callJsonApi("knowledge", {
          action: "upload",
          files: fileData,
        });
        if (result.status === "ok") {
          this.message = result.message || `${files.length} file(s) uploaded`;
          await this.loadLibraryFromKB();
        } else {
          this.error = result.error || "Upload failed";
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
        // Refresh library after reindex
        await this.loadLibraryFromKB();
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

  async loadLibraryFromKB() {
    try {
      const r = await callJsonApi("knowledge", { action: "library", limit: 100 });
      if (r.status === "ok" && r.entries) {
        // Add KB entries to the library
        for (const entry of r.entries) {
          const exists = this.entries.find(e => e.question === entry.title && e.source === entry.source);
          if (!exists) {
            this.entries.unshift({
              id: entry.id || Date.now(),
              question: entry.title,
              answer: "",
              tags: entry.tags || [],
              source: entry.source || entry.category_label || "Knowledge Base",
              saved: true,
              createdAt: entry.created_at || new Date().toISOString(),
              format: entry.format || "",
              file: entry.file || "",
            });
          }
        }
        this.persist();
      }
    } catch (e) {}
  },

  async uploadFiles(files) {
    if (!files || !files.length) return;
    this.uploading = true;
    this.error = "";
    try {
      const fileData = [];
      for (const file of files) {
        const text = await file.text();
        fileData.push({ filename: file.name, content: text });
      }
      // Don't specify category — backend auto-detects from file type
      const r = await callJsonApi("knowledge", {
        action: "upload",
        files: fileData,
      });
      if (r.status === "ok") {
        this.message = r.message || `${files.length} file(s) uploaded`;
        await this.loadLibraryFromKB();
      } else {
        this.error = r.error || "Upload failed";
      }
    } catch (e) {
      this.error = "Upload error: " + e.message;
    }
    this.uploading = false;
    setTimeout(() => { this.message = ""; }, 3000);
  },

  async loadGraph() {
    this.loading = true;
    this.error = "";
    try {
      const r = await callJsonApi("knowledge", { action: "graph", limit: 50 });
      if (r.status === "ok" && r.graph) {
        this.graphData = r.graph;
        this.showGraph = true;
      } else {
        this.error = r.error || "Failed to load graph";
      }
    } catch (e) {
      this.error = "Graph error: " + e.message;
    }
    this.loading = false;
  },

  // ═══════════════════════════════════════════════════════════════
  // CATEGORY MANAGEMENT (WordPress-style)
  // ═══════════════════════════════════════════════════════════════

  async createCategory() {
    const name = this.newCategoryName.trim();
    if (!name) return;
    const key = name.toLowerCase().replace(/\s+/g, "_");
    try {
      const r = await callJsonApi("knowledge", {
        action: "create_category",
        category_key: key,
        category_label: name,
      });
      if (r.status === "ok") {
        this.customCategories.push({ key, label: r.label || name });
        this.activeCategory = key;
        this.newCategoryName = "";
        this.showAddCategory = false;
        this.message = "Category created";
        setTimeout(() => { this.message = ""; }, 2000);
      }
    } catch (e) {
      this.error = "Create category failed: " + e.message;
    }
  },

  get allCategories() {
    // Merge built-in + custom categories
    const builtIn = [
      { key: "literature", label: "Literature & Papers" },
      { key: "deep_research", label: "Deep Research" },
      { key: "docking", label: "Docking Results" },
      { key: "drug_analysis", label: "Drug Analysis" },
      { key: "pharmacophore", label: "Pharmacophore" },
      { key: "qsar", label: "QSAR Models" },
      { key: "statistics", label: "Statistics" },
      { key: "faculty", label: "Faculty & Teaching" },
      { key: "wetlab", label: "Wet Lab" },
      { key: "books", label: "Books & References" },
      { key: "protocols", label: "Protocols & Methods" },
      { key: "data_files", label: "Data Files" },
      { key: "notes", label: "Notes" },
      { key: "misc", label: "Miscellaneous" },
    ];
    return [...builtIn, ...this.customCategories];
  },

  // ═══════════════════════════════════════════════════════════════
  // FILE SELECTION (checkboxes for "Use Selected")
  // ═══════════════════════════════════════════════════════════════

  toggleSelection(id) {
    const idx = this.selectedIds.indexOf(id);
    if (idx >= 0) {
      this.selectedIds.splice(idx, 1);
    } else {
      this.selectedIds.push(id);
    }
  },

  isSelected(id) {
    return this.selectedIds.includes(id);
  },

  selectAll() {
    if (this.selectedIds.length === this.recentEntries.length) {
      this.selectedIds = [];
    } else {
      this.selectedIds = this.recentEntries.map(e => e.id);
    }
  },

  clearSelection() {
    this.selectedIds = [];
  },

  // Entries filtered by active category
  get categoryFilteredEntries() {
    if (this.activeCategory === "all") {
      return this.recentEntries;
    }
    return this.recentEntries.filter(e => {
      const tags = e.tags || [];
      const cat = e.category || (tags[0] || "");
      return tags.includes(this.activeCategory) || cat === this.activeCategory;
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // "USE SELECTED" — send selected files to other modules
  // ═══════════════════════════════════════════════════════════════

  async getSelectedContent() {
    if (!this.selectedIds.length) return null;
    try {
      const r = await callJsonApi("knowledge", {
        action: "selected_entries",
        entry_ids: this.selectedIds,
      });
      if (r.status === "ok") {
        return r.entries;
      }
    } catch (e) {
      this.error = "Failed to load selected: " + e.message;
    }
    return null;
  },

  async useSelectedFor(target) {
    /** Send selected files to: thesis, review, podcast, ppt */
    if (!this.selectedIds.length) {
      this.error = "Select at least one file first";
      setTimeout(() => { this.error = ""; }, 2000);
      return;
    }
    this.loading = true;
    const selected = await this.getSelectedContent();
    if (!selected) {
      this.loading = false;
      return;
    }

    // Combine all selected content into one text block
    const combinedText = selected.map(e =>
      `# ${e.title}\n**Source:** ${e.source || ""}\n\n${e.content}`
    ).join("\n\n---\n\n");

    // Route to the target module
    if (target === "podcast") {
      this.podcastText = combinedText;
      this.activeTab = "podcast";
      this.message = `${selected.length} files loaded for podcast`;
    } else if (target === "thesis") {
      // Open thesis writer and inject the content
      if (window.$store && window.$store.desktopWorkspace) {
        window.$store.desktopWorkspace.openWindow("thesis");
      }
      setTimeout(() => {
        const input = document.querySelector(".aw-source-input, .aw-topic-input");
        if (input) {
          input.value = combinedText.substring(0, 50000);
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }, 500);
      this.message = `${selected.length} files sent to Thesis Writer`;
    } else if (target === "review") {
      // Open literature review
      if (window.$store && window.$store.desktopWorkspace) {
        window.$store.desktopWorkspace.openWindow("review");
      }
      setTimeout(() => {
        const input = document.querySelector(".aw-source-input, .lit-review-input");
        if (input) {
          input.value = combinedText.substring(0, 50000);
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }, 500);
      this.message = `${selected.length} files sent to Review Writer`;
    } else if (target === "ppt") {
      // Open PPT generator
      if (window.$store && window.$store.desktopWorkspace) {
        window.$store.desktopWorkspace.openWindow("slides");
      }
      setTimeout(() => {
        const input = document.querySelector(".slides-topic-input, .aw-topic-input");
        if (input) {
          input.value = combinedText.substring(0, 30000);
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }, 500);
      this.message = `${selected.length} files sent to PPT Generator`;
    } else if (target === "export") {
      // Download as combined text
      const blob = new Blob([combinedText], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kb_export_${Date.now()}.txt`;
      a.click();
      URL.revokeObjectURL(url);
      this.message = `${selected.length} files exported`;
    }

    setTimeout(() => { this.message = ""; }, 3000);
    this.loading = false;
  },

  async moveToCategory(categoryKey) {
    /** Move selected files to a category. */
    if (!this.selectedIds.length) return;
    for (const id of this.selectedIds) {
      try {
        await callJsonApi("knowledge", {
          action: "move_to_category",
          entry_id: id,
          category: categoryKey,
        });
      } catch (e) {}
    }
    this.message = `${this.selectedIds.length} files moved to ${categoryKey}`;
    setTimeout(() => { this.message = ""; }, 3000);
    this.clearSelection();
    await this.loadAllEntries();
  },
});


