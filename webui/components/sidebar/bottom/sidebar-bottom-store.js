import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "v7.5.9",
  commitTime: "",

  get versionLabel() {
    // Always show current version — gitinfo may have stale tags
    return `BioDockify v7.5.9`;
  },

  init() {
    const gi = globalThis.gitinfo;
    if (gi && gi.commit_time) {
      this.commitTime = gi.commit_time;
    }
  },
};

export const store = createStore("sidebarBottom", model);

