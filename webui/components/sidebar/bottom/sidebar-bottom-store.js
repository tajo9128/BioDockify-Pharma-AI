import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "v7.9.7",
  commitTime: "",

  get versionLabel() {
    // Always show current version — gitinfo may have stale tags
    return `BioDockify v7.9.7`;
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.commit_time) {
      this.commitTime = gi.commit_time;
    }
  },
};

export const store = createStore("sidebarBottom", model);

