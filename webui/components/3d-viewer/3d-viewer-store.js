import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("viewer3d", {
  jobId: "",
  loading: false,
  error: "",
  pdbContent: "",
  sdfContent: "",
  poseIndex: 0,

  async loadPose(jobId, pose = 0) {
    if (!jobId) return;
    this.jobId = jobId;
    this.poseIndex = pose;
    this.loading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("pose_get", { job_id: jobId, pose });
      if (resp.error) { this.error = resp.error; return; }
      this.pdbContent = resp.pdb;
      this.sdfContent = resp.sdf;
      // Load NGL viewer after content is ready
      this.$nextTick(() => this.renderNGL());
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  renderNGL() {
    // NGL will be initialized by the template after DOM update
    const event = new CustomEvent("ngl-load", {
      detail: { pdb: this.pdbContent, sdf: this.sdfContent }
    });
    document.dispatchEvent(event);
  }
});
