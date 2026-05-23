import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("journalFinder", {
  mode: "verify", loading: false, error: "", message: "",
  verifyResult: null, suggestResults: [],
  profileResult: null, searchResults: [], searchQuery: "",
  dbStats: null,
  jTitle: "", jIssn: "",
  sTitle: "", sAbstract: "", sKeywords: "", sOaOnly: false, sMaxApc: 0, sQMin: "",
  searchScopus: null, searchWos: null, searchOA: null, searchSubject: "",

  async search() {
    if (!this.searchQuery.trim()) return;
    this.loading = true; this.error = ""; this.searchResults = [];
    try {
      const r = await callJsonApi("journal_finder", {
        action: "search", query: this.searchQuery,
        scopus: this.searchScopus, wos: this.searchWos, oa: this.searchOA,
        subject: this.searchSubject, limit: 30,
      });
      if (r.status === "ok") {
        this.searchResults = r.journals || [];
        this.message = `Found ${r.total} journals (showing ${r.searchResults.length})`;
      } else { this.error = r.error || "Search failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async verify() {
    if (!this.jTitle.trim()) { this.error = "Enter a journal name"; return; }
    this.loading = true; this.error = ""; this.verifyResult = null;
    try {
      const r = await callJsonApi("journal_finder", { action: "verify", title: this.jTitle, issn: this.jIssn });
      if (r.status === "ok") { this.verifyResult = r; this.message = `Verdict: ${r.verdict}`; }
      else { this.error = r.error || "Verification failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async profile() {
    const issn = this.jIssn.trim();
    const title = this.jTitle.trim();
    if (!issn && !title) { this.error = "Enter ISSN or journal name"; return; }
    this.loading = true; this.error = ""; this.profileResult = null;
    try {
      const r = await callJsonApi("journal_finder", { action: "profile", issn, title });
      if (r.status === "ok") { this.profileResult = r; this.message = `Profile: ${r.title}`; }
      else { this.error = r.error || "Profile lookup failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async suggest() {
    if (!this.sTitle.trim()) { this.error = "Enter an article title"; return; }
    this.loading = true; this.error = ""; this.suggestResults = [];
    try {
      const r = await callJsonApi("journal_finder", {
        action: "suggest", title: this.sTitle, abstract: this.sAbstract,
        keywords: this.sKeywords, oa_only: this.sOaOnly,
        max_apc: this.sMaxApc, q_min: this.sQMin,
      });
      if (r.status === "ok") { this.suggestResults = r.suggestions || []; this.message = `${r.count} suggestions`; }
      else { this.error = r.error || "Suggestion failed"; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async loadStats() {
    try {
      const r = await callJsonApi("journal_finder", { action: "stats" });
      if (r.status === "ok") this.dbStats = r;
    } catch (e) {}
  },

  verdictClass(verdict) {
    const map = { "GENUINE": "verdict-genuine", "LIKELY_GENUINE": "verdict-likely", "PREDATORY": "verdict-predatory", "UNVERIFIED": "verdict-unverified" };
    return map[verdict] || "";
  },
  verdictIcon(verdict) {
    const map = { "GENUINE": "verified", "LIKELY_GENUINE": "check_circle", "PREDATORY": "warning", "UNVERIFIED": "help" };
    return map[verdict] || "help";
  },
  verdictLabel(verdict) {
    const map = { "GENUINE": "Genuine — Indexed in major databases", "LIKELY_GENUINE": "Likely Genuine — Verified in at least one source", "PREDATORY": "Predatory Risk — Review carefully before submitting", "UNVERIFIED": "Unverified — Cannot confirm legitimacy" };
    return map[verdict] || String(verdict);
  },
});
