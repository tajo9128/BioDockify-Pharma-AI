import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("docking", {
  step: 1,
  proteinPdb: "",
  ligandSmiles: "",
  ligandName: "ligand",
  jobId: "",
  receptorPath: "",
  ligandPath: "",
  center: { x: 0, y: 0, z: 0 },
  size: { x: 20, y: 20, z: 20 },
  loading: false,
  results: null,
  error: "",
  jobStatus: "",

  reset() {
    this.step = 1;
    this.proteinPdb = "";
    this.ligandSmiles = "";
    this.ligandName = "ligand";
    this.jobId = "";
    this.receptorPath = "";
    this.ligandPath = "";
    this.center = { x: 0, y: 0, z: 0 };
    this.size = { x: 20, y: 20, z: 20 };
    this.loading = false;
    this.results = null;
    this.error = "";
    this.jobStatus = "";
  },

  async uploadAndPrepare() {
    if (!this.proteinPdb || !this.ligandSmiles) {
      this.error = "Upload a protein PDB and enter a ligand SMILES";
      return;
    }
    this.loading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("docking_prepare", {
        protein_pdb: this.proteinPdb,
        ligand_smiles: this.ligandSmiles,
        ligand_name: this.ligandName
      });
      if (resp.error) { this.error = resp.error; return; }
      this.jobId = resp.job_id;
      this.receptorPath = resp.receptor_pdbqt;
      this.ligandPath = resp.ligand_pdbqt;
      this.center = resp.center;
      this.size = resp.size;
      this.step = 2;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async runDocking() {
    this.loading = true;
    this.error = "";
    this.jobStatus = "Running Vina docking...";
    try {
      const resp = await callJsonApi("docking_run", {
        job_id: this.jobId,
        receptor_pdbqt: this.receptorPath,
        ligand_pdbqt: this.ligandPath,
        center: this.center,
        size: this.size
      });
      if (resp.error) { this.error = resp.error; return; }
      this.results = resp;
      this.step = 3;
      this.jobStatus = "Complete";
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  triggerFileUpload() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdb,.ent";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      this.proteinPdb = await file.text();
    };
    input.click();
  }
});
