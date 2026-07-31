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

  // Source/time filters
  recentFilter: "all",    // "all" | "7d" | "30d"
  sourceFilter: "all",    // "all" or a source module name

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

  // Simple markdown-to-HTML renderer (no external dependency)
  renderMarkdown(text) {
    if (!text) return "";
    let html = text;

    // Escape HTML first
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Code blocks ```...```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background:var(--color-panel);padding:10px;border-radius:6px;overflow-x:auto;font-size:0.65rem;border:1px solid var(--color-border)"><code>$2</code></pre>');

    // Headings (### before ## before #)
    html = html.replace(/^#### (.+)$/gm, '<h4 style="font-size:0.85rem;color:var(--color-primary);margin:12px 0 4px">$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:0.9rem;color:var(--color-primary);margin:12px 0 4px">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:1rem;color:var(--color-primary);margin:14px 0 6px;border-bottom:1px solid var(--color-border);padding-bottom:4px">$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 style="font-size:1.15rem;color:var(--color-primary);margin:16px 0 8px">$1</h1>');

    // Bold **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic *text* (but not ** **)
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

    // Horizontal rules ---
    html = html.replace(/^---+$/gm, '<hr style="border:none;border-top:1px solid var(--color-border);margin:12px 0">');

    // Unordered list items - item or * item
    html = html.replace(/^[\-\*] (.+)$/gm, '<li style="margin-left:20px;list-style:disc;margin-bottom:3px">$1</li>');

    // Ordered list items 1. item
    html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin-left:20px;list-style:decimal;margin-bottom:3px">$1</li>');

    // Links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:var(--color-primary);text-decoration:underline">$1</a>');

    // DOI links
    html = html.replace(/doi:\s*(10\.\d{4,9}\/[^\s<]+)/gi, '<a href="https://doi.org/$1" target="_blank" style="color:var(--color-primary)">doi:$1</a>');

    // PMID links
    html = html.replace(/PMID[:\s]*(\d{6,8})/gi, '<a href="https://pubmed.ncbi.nlm.nih.gov/$1/" target="_blank" style="color:var(--color-primary)">PMID: $1</a>');

    // Tables (simple markdown tables)
    html = html.replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      if (cells.every(c => c.trim().match(/^[-:]+$/))) return ''; // separator row
      return '<tr>' + cells.map(c => `<td style="border:1px solid var(--color-border);padding:4px 8px;font-size:0.65rem">${c.trim()}</td>`).join('') + '</tr>';
    });
    // Wrap consecutive <tr> in <table>
    html = html.replace(/(<tr>[\s\S]*?<\/tr>)/g, '<table style="border-collapse:collapse;width:100%;margin:8px 0">$1</table>');

    // Paragraphs — wrap blocks separated by blank lines
    html = html.split(/\n\n+/).map(block => {
      block = block.trim();
      if (!block) return '';
      if (block.startsWith('<')) return block; // already HTML
      return '<p style="margin:8px 0;line-height:1.7">' + block.replace(/\n/g, '<br>') + '</p>';
    }).join('\n');

    return html;
  },

  async downloadDocx() {
    /** Download the current reading entry as DOCX */
    if (!this.readingPaper) return;
    const file = this.readingPaper.file || "";
    const docxFile = file.replace(/\.md$/, '.docx');
    if (docxFile !== file) {
      // Try downloading the .docx version
      try {
        const csrfResp = await fetch("/api/csrf_token");
        const csrfData = await csrfResp.json();
        const resp = await fetch("/api/knowledge", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfData.csrf_token || "" },
          body: JSON.stringify({ action: "download_docx", file: docxFile }),
        });
        if (resp.ok) {
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = (this.readingPaper.title || "article").substring(0, 50) + ".docx";
          a.click();
          URL.revokeObjectURL(url);
          this.message = "DOCX downloaded";
          setTimeout(() => { this.message = ""; }, 3000);
          return;
        }
      } catch (e) {}
    }
    // Fallback: download as .txt
    const content = this.readingPaper.full_text || this.readingPaper.answer || "";
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (this.readingPaper.title || "article").substring(0, 50) + ".txt";
    a.click();
    URL.revokeObjectURL(url);
    this.message = "Text downloaded";
    setTimeout(() => { this.message = ""; }, 3000);
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
      if (r.status === "ok") {
        // Update the entry with full content + original file metadata
        const idx = this.entries.findIndex(e => e.id === entry.id);
        if (idx >= 0) {
          this.entries[idx].answer = r.content;
          this.entries[idx]._fullyLoaded = true;
          this.entries[idx].has_original = r.has_original;
          this.entries[idx].file_type = r.file_type;
        }
        // Open in reader view — include original file metadata for PDF/image viewer
        this.readingPaper = {
          ...entry,
          full_text: r.content || "",
          answer: r.content || "",
          has_original: r.has_original || false,
          file_type: r.file_type || "md",
          entry_id: entry.id,
        };
      } else {
        this.readingPaper = entry;
      }
    } catch (e) {
      this.error = "Failed to read entry: " + e.message;
    }
    this.loading = false;
  },

  async viewOriginal() {
    /** Open the original PDF/DOCX in a new tab. Fetches blob then opens object URL. */
    if (!this.readingPaper?.entry_id) return;
    try {
      const csrfResp = await fetch("/api/csrf_token");
      const csrfData = await csrfResp.json();
      const resp = await fetch("/api/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfData.csrf_token || "" },
        body: JSON.stringify({ action: "view_file", entry_id: this.readingPaper.entry_id }),
      });
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      } else {
        this.error = "Failed to view original file";
      }
    } catch (e) {
      this.error = "View failed: " + e.message;
    }
  },

  async downloadOriginal() {
    /** Download the original binary file (PDF/DOCX). */
    if (!this.readingPaper?.entry_id) return;
    try {
      const csrfResp = await fetch("/api/csrf_token");
      const csrfData = await csrfResp.json();
      const resp = await fetch("/api/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfData.csrf_token || "" },
        body: JSON.stringify({ action: "download_original", entry_id: this.readingPaper.entry_id }),
      });
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = (this.readingPaper.title || "file").substring(0, 50);
        a.click();
        URL.revokeObjectURL(url);
      } else {
        this.error = "Failed to download original file";
      }
    } catch (e) {
      this.error = "Download failed: " + e.message;
    }
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

  get filteredBySource() {
    let list = this.categoryFilteredEntries;
    // Apply recent filter
    if (this.recentFilter === "7d") {
      const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
      list = list.filter(e => {
        const d = new Date(e.createdAt || 0).getTime();
        return d >= cutoff;
      });
    } else if (this.recentFilter === "30d") {
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      list = list.filter(e => {
        const d = new Date(e.createdAt || 0).getTime();
        return d >= cutoff;
      });
    }
    // Apply source filter
    if (this.sourceFilter && this.sourceFilter !== "all") {
      list = list.filter(e => (e.source || e.source_module || "").includes(this.sourceFilter));
    }
    return list;
  },

  relativeTime(dateStr) {
    if (!dateStr) return "";
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diff = now - then;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    const days = Math.floor(hrs / 24);
    if (days < 30) return days + "d ago";
    const months = Math.floor(days / 30);
    return months + "mo ago";
  },

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

  toggleSelectAll() {
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
  },

  async sendMessage() {
    if (!this.chatInput.trim()) return;
    const msg = this.chatInput.trim();
    this.chatMessages.push({ role: "user", content: msg });
    this.chatInput = "";
    this.chatLoading = true;
    try {
      // Real RAG: call kb_chat API (hybrid search + LLM + citations)
      const r = await callJsonApi("knowledge", {
        action: "kb_chat",
        query: msg,
        top_k: 8,
      });
      if (r.status === "ok") {
        // Render answer with citation links
        let answer = r.answer || "No answer generated.";
        // Attach clickable citations
        const citations = r.citations || [];
        if (citations.length > 0) {
          answer += "\n\n**Sources:**\n";
          for (const c of citations) {
            answer += `[${c.label}] ${c.display}\n`;
          }
        }
        this.chatMessages.push({ role: "assistant", content: answer });
        // Store citations for the UI to render as clickable links
        this._lastCitations = citations;
      } else {
        this.chatMessages.push({ role: "assistant", content: r.error || "KB chat failed." });
      }
    } catch (e) {
      this.chatMessages.push({ role: "assistant", content: "Error: " + e.message });
    }
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
      // Load KB status and categories
      const r = await callJsonApi("knowledge", { action: "status" });
      if (r.status === "ok") {
        this.kbStatus = r;
        const kbCats = [];
        const labels = r.category_labels || {};
        for (const [key, count] of Object.entries(r.categories || {})) {
          kbCats.push({ name: key, label: labels[key] || key, count: count, source: "kb" });
        }
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
      // Load KB entries into entries array
      const r2 = await callJsonApi("knowledge", { action: "library", limit: 100 });
      if (r2.status === "ok" && r2.entries) {
        for (const entry of r2.entries) {
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
    } catch (e) { console.error("loadLibraryFromKB failed:", e); }
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

  triggerUploadRestore() {
    /** File picker → upload to Knowledge Base. This is the method called by the UI buttons. */
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.pdf,.txt,.md,.json,.docx,.xlsx,.xls,.html,.htm,.sdf,.mol,.pdb,.pdbqt,.mp3,.wav,.mp4,.avi,.png,.jpg,.jpeg";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = e.target.files;
      if (!files || !files.length) return;
      this.uploading = true;
      this.error = "";
      this.message = `Uploading ${files.length} file(s)...`;
      try {
        const fileData = [];
        for (const file of files) {
          // Read as text for text-based files; for binary (PDF/DOCX/XLSX), send filename only
          const ext = file.name.split('.').pop().toLowerCase();
          if (["pdf", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "mp3", "wav", "mp4", "avi"].includes(ext)) {
            // Binary file — read as base64
            const reader = new FileReader();
            const base64 = await new Promise((resolve) => {
              reader.onload = () => {
                const result = reader.result;
                // Strip data URL prefix if present
                const base64 = result.includes(",") ? result.split(",")[1] : result;
                resolve(base64);
              };
              reader.readAsDataURL(file);
            });
            fileData.push({ filename: file.name, content: base64 });
          } else {
            // Text file — read as text
            const text = await file.text();
            fileData.push({ filename: file.name, content: text });
          }
        }
        const result = await callJsonApi("knowledge", {
          action: "upload",
          files: fileData,
        });
        if (result.status === "ok") {
          this.message = result.message || `${files.length} file(s) uploaded`;
          setTimeout(() => { this.message = ""; }, 4000);
          await this.loadAllEntries();
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
          const ext = file.name.split('.').pop().toLowerCase();
          if (["pdf", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "mp3", "wav", "mp4", "avi"].includes(ext)) {
            const reader = new FileReader();
            const base64 = await new Promise((resolve) => {
              reader.onload = () => {
                const result = reader.result;
                resolve(result.includes(",") ? result.split(",")[1] : result);
              };
              reader.readAsDataURL(file);
            });
            fileData.push({ filename: file.name, content: base64 });
          } else {
            const text = await file.text();
            fileData.push({ filename: file.name, content: text });
          }
        }
        const result = await callJsonApi("knowledge", { action: "upload", files: fileData });
        if (result.status === "ok") {
          this.message = result.message || `${files.length} file(s) uploaded`;
          await this.loadAllEntries();
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

  // ─── Obsidian Integration ─────────────────────────────────────────────

  async sendToObsidian() {
    /** Export selected KB entries to Obsidian vault as .md with YAML frontmatter */
    if (!this.selectedIds.length) {
      this.error = "Select at least one file first";
      setTimeout(() => { this.error = ""; }, 2000);
      return;
    }
    this.loading = true;
    try {
      const r = await callJsonApi("obsidian_sync", {
        action: "export",
        entry_ids: Array.from(this.selectedIds),
      });
      if (r.status === "ok") {
        this.message = r.message || `Exported ${r.exported || 0} files to Obsidian vault`;
      } else {
        this.error = r.error || "Export failed";
      }
    } catch (e) {
      this.error = "Obsidian sync error: " + e.message;
    }
    this.loading = false;
    setTimeout(() => { this.message = ""; this.error = ""; }, 4000);
  },

  async pullFromObsidian() {
    /** Import .md files from Obsidian vault into BioDockify KB */
    this.loading = true;
    try {
      const r = await callJsonApi("obsidian_sync", { action: "import" });
      if (r.status === "ok") {
        this.message = r.message || `Imported ${r.imported || 0} files from Obsidian`;
        // Refresh the entry list
        await this.loadAllEntries();
      } else {
        this.error = r.error || "Import failed";
      }
    } catch (e) {
      this.error = "Obsidian sync error: " + e.message;
    }
    this.loading = false;
    setTimeout(() => { this.message = ""; this.error = ""; }, 4000);
  },

  async obsidianStatus() {
    /** Check Obsidian vault status (file count, categories, last modified) */
    try {
      const r = await callJsonApi("obsidian_sync", { action: "status" });
      if (r.status === "ok") {
        return r;
      }
    } catch (e) { /* silent */ }
    return { exists: false, file_count: 0, categories: [] };
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

  // ═══════════════════════════════════════════════════════════════
  // NOTEBOOK LM — Notebooks, Sources, Notes, Transformations, Podcast
  // ═══════════════════════════════════════════════════════════════

  // Notebook state
  notebooks: [],
  activeNotebookId: null,
  notebookSources: [],
  notebookNotes: [],
  showNotebooks: false,  // toggle between file list and notebook view

  // Transformations
  transformations: [],
  showTransformations: false,

  // Podcast (enhanced — from notebook)
  podcastTopic: "",
  podcastFormat: "interview",
  podcastTone: "professional",
  podcastLength: "medium",
  podcastSpeakers: [
    { name: "Host", persona: "Research host" },
    { name: "Expert", persona: "Domain expert" },
  ],
  podcastPrompt: "",  // generated prompt to send to agent

  // Chat in notebook
  nbChatMessages: [],
  nbChatInput: "",
  nbChatLoading: false,

  // Load all notebooks
  async loadNotebooks() {
    try {
      const r = await callJsonApi("knowledge", { action: "list_notebooks" });
      if (r.status === "ok") {
        this.notebooks = r.notebooks || [];
      }
    } catch (e) {
      console.error("loadNotebooks failed:", e);
    }
  },

  // Create a new notebook
  async createNotebook(name, description) {
    if (!name?.trim()) return;
    try {
      const r = await callJsonApi("knowledge", {
        action: "create_notebook",
        name: name.trim(),
        description: description || "",
      });
      if (r.status === "ok" && r.notebook) {
        this.notebooks.push(r.notebook);
        this.activeNotebookId = r.notebook.id;
        this.message = "Notebook created";
        setTimeout(() => { this.message = ""; }, 2000);
        return r.notebook;
      } else {
        this.error = r.error || "Failed to create notebook";
      }
    } catch (e) {
      this.error = "Create notebook failed: " + e.message;
    }
  },

  // Delete a notebook
  async deleteNotebook(nbId) {
    try {
      await callJsonApi("knowledge", { action: "delete_notebook", notebook_id: nbId });
      this.notebooks = this.notebooks.filter(n => n.id !== nbId);
      if (this.activeNotebookId === nbId) {
        this.activeNotebookId = null;
        this.notebookSources = [];
        this.notebookNotes = [];
      }
      this.message = "Notebook deleted";
      setTimeout(() => { this.message = ""; }, 2000);
    } catch (e) {
      this.error = "Delete failed: " + e.message;
    }
  },

  // Open a notebook — loads sources and notes
  async openNotebook(nbId) {
    this.activeNotebookId = nbId;
    this.showNotebooks = true;
    await this.loadNotebookSources(nbId);
    await this.loadNotebookNotes(nbId);
  },

  // Get active notebook object
  get activeNotebook() {
    return this.notebooks.find(n => n.id === this.activeNotebookId) || null;
  },

  // Add a KB source to the active notebook
  async addSourceToNotebook(entryId, contextLevel) {
    if (!this.activeNotebookId) return;
    try {
      const r = await callJsonApi("knowledge", {
        action: "add_source_to_notebook",
        notebook_id: this.activeNotebookId,
        entry_id: entryId,
        context_level: contextLevel || "full",
      });
      if (r.status === "ok") {
        await this.loadNotebookSources(this.activeNotebookId);
        this.message = "Source added to notebook";
        setTimeout(() => { this.message = ""; }, 2000);
      }
    } catch (e) {
      this.error = "Add source failed: " + e.message;
    }
  },

  // Remove a source from the active notebook
  async removeSourceFromNotebook(entryId) {
    if (!this.activeNotebookId) return;
    try {
      await callJsonApi("knowledge", {
        action: "remove_source_from_notebook",
        notebook_id: this.activeNotebookId,
        entry_id: entryId,
      });
      this.notebookSources = this.notebookSources.filter(s => s.entry_id !== entryId);
      this.message = "Source removed";
      setTimeout(() => { this.message = ""; }, 2000);
    } catch (e) {
      this.error = "Remove source failed: " + e.message;
    }
  },

  // Load sources for a notebook
  async loadNotebookSources(nbId) {
    // Sources are embedded in the notebook object
    const nb = this.notebooks.find(n => n.id === (nbId || this.activeNotebookId));
    if (!nb) { this.notebookSources = []; return; }
    // Resolve source entries from the main entries list
    const sources = nb.sources || [];
    this.notebookSources = sources.map(s => {
      const entry = this.entries.find(e => e.id === s.entry_id || e.id == s.entry_id);
      return {
        ...s,
        title: entry?.question || entry?.title || s.entry_id,
        source: entry?.source || "",
        category: (entry?.tags || [])[0] || "",
        file: entry?.file || "",
      };
    });
  },

  // Add a note to the active notebook
  async addNotebookNote(content, author) {
    if (!this.activeNotebookId || !content?.trim()) return;
    try {
      const r = await callJsonApi("knowledge", {
        action: "add_note",
        notebook_id: this.activeNotebookId,
        content: content.trim(),
        author: author || "manual",
      });
      if (r.status === "ok" && r.note) {
        this.notebookNotes.push(r.note);
        this.message = "Note added";
        setTimeout(() => { this.message = ""; }, 2000);
      }
    } catch (e) {
      this.error = "Add note failed: " + e.message;
    }
  },

  // Load notes for a notebook
  async loadNotebookNotes(nbId) {
    try {
      const r = await callJsonApi("knowledge", {
        action: "list_notes",
        notebook_id: nbId || this.activeNotebookId,
      });
      if (r.status === "ok") {
        this.notebookNotes = r.notes || [];
      }
    } catch (e) {
      this.notebookNotes = [];
    }
  },

  // Delete a note
  async deleteNotebookNote(noteId) {
    if (!this.activeNotebookId) return;
    try {
      await callJsonApi("knowledge", {
        action: "delete_note",
        notebook_id: this.activeNotebookId,
        note_id: noteId,
      });
      this.notebookNotes = this.notebookNotes.filter(n => n.id !== noteId);
    } catch (e) {
      this.error = "Delete note failed: " + e.message;
    }
  },

  // Load transformations
  async loadTransformations() {
    try {
      const r = await callJsonApi("knowledge", { action: "list_transformations" });
      if (r.status === "ok") {
        this.transformations = r.transformations || [];
      }
    } catch (e) {}
  },

  // Create a transformation
  async createTransformation(name, promptTemplate) {
    if (!name?.trim() || !promptTemplate?.trim()) return;
    try {
      const r = await callJsonApi("knowledge", {
        action: "create_transformation",
        name: name.trim(),
        prompt_template: promptTemplate.trim(),
      });
      if (r.status === "ok" && r.transformation) {
        this.transformations.push(r.transformation);
        this.message = "Transformation created";
        setTimeout(() => { this.message = ""; }, 2000);
      }
    } catch (e) {
      this.error = "Create transformation failed: " + e.message;
    }
  },

  // Run a transformation on a source — returns prompt for agent
  async runTransformation(tfId, entryId) {
    if (!this.activeNotebookId) return;
    try {
      const r = await callJsonApi("knowledge", {
        action: "run_transformation",
        transformation_id: tfId,
        entry_id: entryId,
        notebook_id: this.activeNotebookId,
      });
      if (r.status === "ok" && r.prompt) {
        // Send the prompt to the agent for processing
        this.nbChatMessages.push({ role: "user", content: r.prompt });
        this.message = `Running: ${r.transformation_name}`;
        setTimeout(() => { this.message = ""; }, 3000);
      } else {
        this.error = r.error || "Transformation failed";
      }
    } catch (e) {
      this.error = "Run transformation failed: " + e.message;
    }
  },

  // Generate podcast prompt from notebook sources
  async generateNotebookPodcast() {
    if (!this.activeNotebookId) {
      this.error = "Open a notebook first";
      return;
    }
    try {
      const r = await callJsonApi("knowledge", {
        action: "generate_podcast",
        notebook_id: this.activeNotebookId,
        speakers: this.podcastSpeakers,
        topic: this.podcastTopic || "",
        format: this.podcastFormat,
        tone: this.podcastTone,
        length: this.podcastLength,
      });
      if (r.status === "ok" && r.prompt) {
        this.podcastPrompt = r.prompt;
        // Send to agent chat
        this.nbChatMessages.push({
          role: "user",
          content: r.prompt,
        });
        this.message = `Podcast prompt built (${r.source_count} sources). Sent to agent.`;
        setTimeout(() => { this.message = ""; }, 5000);
      } else {
        this.error = r.error || "Podcast generation failed";
      }
    } catch (e) {
      this.error = "Podcast error: " + e.message;
    }
  },

  // Notebook chat — send message with notebook context
  async sendNotebookChat() {
    if (!this.nbChatInput.trim()) return;
    const msg = this.nbChatInput.trim();
    this.nbChatMessages.push({ role: "user", content: msg });
    this.nbChatInput = "";
    this.nbChatLoading = true;
    try {
      // Build context from notebook sources + notes
      const sourceContext = this.notebookSources.map(s =>
        `[Source: ${s.title}]`
      ).join("\n");
      const noteContext = this.notebookNotes.map(n =>
        `[Note by ${n.author}]: ${n.content}`
      ).join("\n");
      const context = `Notebook: ${this.activeNotebook?.name || ""}\n\nSources:\n${sourceContext}\n\nNotes:\n${noteContext}\n\nUser: ${msg}`;
      // Route to Agent Zero chat
      const input = document.getElementById("chat-input") || document.querySelector("textarea[data-chat-input]");
      if (input) {
        input.value = context;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
      }
      this.nbChatMessages.push({
        role: "assistant",
        content: "Sent to Agent Zero with notebook context. Check the chat panel for the response.",
      });
    } catch (e) {
      this.nbChatMessages.push({ role: "assistant", content: "Error: " + e.message });
    }
    this.nbChatLoading = false;
  },

  // Toggle between file list and notebook view
  toggleNotebookView() {
    this.showNotebooks = !this.showNotebooks;
    if (this.showNotebooks && !this.notebooks.length) {
      this.loadNotebooks();
    }
  },
});


