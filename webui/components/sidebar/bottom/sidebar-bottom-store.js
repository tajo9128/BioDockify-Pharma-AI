import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "",
  commitTime: "",

  get versionLabel() {
    // Always show current version — gitinfo may have stale tags
    const v = globalThis.gitinfo?.version || this.versionNo || "";
    return v ? `BioDockify v${v}` : "BioDockify";
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi) {
      if (gi.version) this.versionNo = gi.version;
      if (gi.commit_time) this.commitTime = gi.commit_time;
    }
  },
};

export const store = createStore("sidebarBottom", model);

