import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("admet", {
  smiles: "",
  preset: "",
  loading: false,
  result: null,
  error: "",
  libraries: ["aspirin", "ibuprofen", "metformin", "caffeine", "warfarin", "sildenafil"],

  get libraryNames() {
    return { aspirin: "Aspirin", ibuprofen: "Ibuprofen", metformin: "Metformin", caffeine: "Caffeine", warfarin: "Warfarin", sildenafil: "Sildenafil" };
  },

  selectPreset(name) { this.preset = name; this.smiles = ""; this.result = null; this.analyze(); },

  async analyze() {
    if (!this.smiles && !this.preset) return;
    this.loading = true; this.error = "";
    try {
      const resp = await callJsonApi("admet_predict", { smiles: this.smiles, preset: this.preset });
      if (resp.error) { this.error = resp.error; } else { this.result = resp; }
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() { this.smiles = ""; this.preset = ""; this.result = null; this.error = ""; }
});
