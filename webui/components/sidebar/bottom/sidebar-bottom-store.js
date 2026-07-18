import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "v7.5.2",
  commitTime: "",

  get versionLabel() {
    // Always show v7.5.2 — gitinfo may have stale tags
    return `BioDockify v7.5.2`;
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.commit_time) {
      this.commitTime = gi.commit_time;
    }
  },
};

export const store = createStore("sidebarBottom", model);

