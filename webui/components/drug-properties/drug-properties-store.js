import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("drugProperties", {
  smiles: "",
  preset: "",
  loading: false,
  result: null,
  error: "",
  libraries: ["aspirin", "caffeine", "ibuprofen", "metformin", "morphine", "warfarin", "sildenafil", "glucose"],

  get libraryNames() {
    return {
      aspirin: "Aspirin", caffeine: "Caffeine", ibuprofen: "Ibuprofen",
      metformin: "Metformin", morphine: "Morphine", warfarin: "Warfarin",
      sildenafil: "Sildenafil", glucose: "Glucose"
    };
  },

  selectPreset(name) {
    this.preset = name;
    this.smiles = "";
    this.result = null;
    this.error = "";
    this.analyze();
  },

  async analyze() {
    if (!this.smiles && !this.preset) return;
    this.loading = true;
    this.error = "";
    this.result = null;
    try {
      const resp = await callJsonApi("drug_properties", {
        smiles: this.smiles,
        preset: this.preset
      });
      if (resp.error) {
        this.error = resp.error;
      } else {
        this.result = resp;
      }
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  clear() {
    this.smiles = "";
    this.preset = "";
    this.result = null;
    this.error = "";
  }
});
