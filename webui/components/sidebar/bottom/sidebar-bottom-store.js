import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "",
  commitTime: "",

  get versionLabel() {
    const v = this.versionNo || "";
    const clean = v.replace(/^M\s*/, "").replace(/^v/, "v");
    // Ensure we show the correct version (override old git tags)
    const num = parseFloat(clean.replace(/^v/, ""));
    return `BioDockify v6.0.3`;
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.version && gi.commit_time) {
      this.versionNo = gi.version;
      this.commitTime = gi.commit_time;
    }
  },
};

export const store = createStore("sidebarBottom", model);

