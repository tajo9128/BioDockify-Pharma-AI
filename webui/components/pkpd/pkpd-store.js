import { callJsonApi } from "/js/api.js";

Alpine.data("pkpdModal", () => ({
  activeTab: "nca",
  loading: false, errorMessage: "", result: null,
  fileName: "", columns: [], rowCount: 0, rows: [],

  // NCA
  timeCol: "Time_h", concCol: "Concentration_ng_ml", doseCol: "Dose_mg",
  dose: 100, compartments: 2,

  // PD
  pdDoseCol: "Dose_mg", pdRespCol: "Effect_Pct",

  openFilePicker() {
    const i = document.createElement("input"); i.type = "file"; i.accept = ".csv";
    i.onchange = (e) => {
      const f = e.target.files?.[0]; i.remove(); if (!f) return;
      this.fileName = f.name; this.loading = true;
      const r = new FileReader();
      r.onload = () => {
        const t = r.result; const lines = t.split("\n").filter(l => l.trim());
        if (lines.length < 2) { this.loading = false; return; }
        this.columns = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
        this.rows = [];
        for (let j = 1; j < lines.length; j++) {
          const vals = lines[j].split(",").map(v => v.trim().replace(/^"|"$/g, ""));
          this.rows.push(vals);
        }
        this.rowCount = this.rows.length;
        // Auto-detect columns
        if (this.columns.some(c => c.toLowerCase().includes("time"))) this.timeCol = this.columns.find(c => c.toLowerCase().includes("time"));
        if (this.columns.some(c => c.toLowerCase().includes("conc"))) this.concCol = this.columns.find(c => c.toLowerCase().includes("conc"));
        this.loading = false;
      };
      r.readAsText(f);
    };
    document.body.appendChild(i); i.click();
  },

  async run(method) {
    this.loading = true; this.errorMessage = ""; this.result = null;
    try {
      const data = {};
      for (let ri = 0; ri < this.rows.length; ri++) {
        const row = {};
        for (let ci = 0; ci < this.columns.length; ci++) row[this.columns[ci]] = this.rows[ri][ci] || "";
        data[ri] = row;
      }
      const payload = { action: method, data: data, time_col: this.timeCol, conc_col: this.concCol, dose_col: this.doseCol };
      if (method === "compartmental") { payload.dose = parseFloat(this.dose) || 100; payload.compartments = this.compartments; }
      if (method === "pd_response") { payload.dose_col = this.pdDoseCol; payload.response_col = this.pdRespCol; }
      const r = await callJsonApi("pkpd", payload);
      if (r.status === "ok") this.result = r.results || r;
      else this.errorMessage = r.error || "Analysis failed";
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry("PK/PD — " + this.fileName, JSON.stringify(this.result,null,2), "PK/PD Analysis", ["pkpd","pharmacokinetics"]);
    }
  },
  resetData() { this.fileName = ""; this.columns = []; this.rows = []; this.result = null; this.errorMessage = ""; },
}));
