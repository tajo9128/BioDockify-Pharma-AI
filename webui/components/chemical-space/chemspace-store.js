import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("chemicalSpace", {
  smilesList: "",
  loading: false,
  plotUrl: "",
  error: "",

  async explore() {
    const lines = this.smilesList.trim().split("\n").filter(s => s.trim());
    if (lines.length < 2) { this.error = "Enter at least 2 SMILES"; return; }
    this.loading = true; this.error = "";
    try {
      const resp = await callJsonApi("chemical_space", { smiles_list: lines });
      if (resp.error) { this.error = resp.error; return; }
      this.plotUrl = "data:image/png;base64," + resp.plot_base64;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() { this.smilesList = ""; this.plotUrl = ""; this.error = ""; }
});
