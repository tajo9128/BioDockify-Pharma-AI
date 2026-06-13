import { callJsonApi } from "/js/api.js";

Alpine.data("proteinPrep", () => ({
  loading: false, errorMessage: "", result: null,
  fileName: "", pdbContent: "", dragover: false,
  ph: 7.4,

  init() {},
  onOpen() { this.checkHealth(); },

  async checkHealth() {
    try { await callJsonApi("protein_prep", { action: "health" }); } catch {}
  },

  openFilePicker() {
    const i = document.createElement("input"); i.type = "file"; i.accept = ".pdb";
    i.onchange = (e) => {
      const f = e.target.files?.[0]; i.remove(); if (!f) return;
      this.fileName = f.name; this.loading = true;
      const r = new FileReader();
      r.onload = () => { this.pdbContent = r.result; this.loading = false; };
      r.readAsText(f);
    };
    document.body.appendChild(i); i.click();
  },

  async prepare() {
    this.loading = true; this.errorMessage = ""; this.result = null;
    try {
      const r = await callJsonApi("protein_prep", { action: "prepare", pdb: this.pdbContent, ph: this.ph });
      this.result = r;
      if (r.status === "ok") this.fileName = r.output_path || this.fileName;
      else this.errorMessage = r.error || "Preparation failed";
    } catch (e) { this.errorMessage = "Error: " + (e.message || "API unavailable"); }
    this.loading = false;
  },

  download() {
    if (!this.result?.output_path) return;
    const blob = new Blob([this.pdbContent], { type: "chemical/x-pdb" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = this.result.output_path; a.click();
    URL.revokeObjectURL(url);
  },

  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry("Prepared Protein — " + this.fileName, JSON.stringify(this.result,null,2), "Protein Preparation", ["protein","pdbfixer","preparation"]);
    }
  },

  reset() {
    this.fileName = ""; this.pdbContent = ""; this.result = null; this.errorMessage = "";
  },
}));
