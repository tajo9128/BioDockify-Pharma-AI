import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("molSimilarity", {
  querySmiles: "",
  referenceSmiles: "",
  loading: false,
  results: [],
  error: "",

  async search() {
    if (!this.querySmiles.trim()) return;
    this.loading = true; this.error = "";
    try {
      const resp = await callJsonApi("molecular_similarity", {
        query_smiles: this.querySmiles,
        reference_smiles: this.referenceSmiles || this.querySmiles
      });
      if (resp.error) { this.error = resp.error; return; }
      this.results = resp.results || [];
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() { this.querySmiles = ""; this.referenceSmiles = ""; this.results = []; this.error = ""; }
});
