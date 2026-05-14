import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("drugBrowser", {
  query: "",
  system: "",
  results: [],
  systems: [],
  total: 0,
  loading: false,
  selectedDrug: null,
  selectedProps: {},

  async search() {
    this.loading = true;
    try {
      const resp = await callJsonApi("drug_browser", {
        query: this.query,
        system: this.system,
        action: "search"
      });
      this.results = resp.drugs || [];
      this.systems = resp.systems || [];
      this.total = resp.total || 0;
    } catch (e) { this.results = []; }
    this.loading = false;
  },

  async loadSystems() {
    try {
      const resp = await callJsonApi("drug_browser", { action: "systems" });
      this.systems = resp.systems || [];
    } catch (e) { this.systems = []; }
  },

  filterBySystem(s) {
    this.system = this.system === s ? "" : s;
    this.search();
  },

  async selectDrug(drug) {
    this.selectedDrug = drug;
    try {
      const resp = await callJsonApi("drug_browser", {
        action: "detail", id: drug.id
      });
      this.selectedProps = resp.properties || {};
    } catch (e) { this.selectedProps = {}; }
  },

  clearSelection() { this.selectedDrug = null; this.selectedProps = {}; }
});
