import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("journalFinder", {
  mode: "verify",
  loading: false,
  error: "",
  message: "",

  // Verify
  jTitle: "",
  jIssn: "",
  verifyResult: null,

  // Suggest
  sTitle: "",
  sAbstract: "",
  sKeywords: "",
  sOaOnly: false,
  sMaxApc: "0",
  sQMin: "",
  suggestResults: [],

  async verify() {
    if (!this.jTitle.trim() && !this.jIssn.trim()) return;
    this.loading = true; this.error = ""; this.verifyResult = null;
    try {
      this.verifyResult = await callJsonApi("journal_finder", { mode: "verify", title: this.jTitle, issn: this.jIssn });
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async suggest() {
    if (!this.sTitle.trim()) return;
    this.loading = true; this.error = ""; this.suggestResults = [];
    try {
      const r = await callJsonApi("journal_finder", {
        mode: "suggest", title: this.sTitle, abstract: this.sAbstract,
        keywords: this.sKeywords, oa_only: this.sOaOnly,
        max_apc: this.sMaxApc, q_min: this.sQMin,
      });
      this.suggestResults = r.journals || [];
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  verdictClass(v) {
    return v === "GENUINE" ? "genuine" : v === "LIKELY_GENUINE" ? "likely" : v === "PREDATORY" ? "predatory" : "unverified";
  },
  verdictIcon(v) {
    return v === "GENUINE" ? "✅" : v === "LIKELY_GENUINE" ? "🟡" : v === "PREDATORY" ? "🔴" : "⚪";
  },
  verdictLabel(v) {
    return v === "GENUINE" ? "GENUINE" : v === "LIKELY_GENUINE" ? "LIKELY GENUINE" : v === "PREDATORY" ? "PREDATORY — DO NOT SUBMIT" : "UNVERIFIED";
  },
});
