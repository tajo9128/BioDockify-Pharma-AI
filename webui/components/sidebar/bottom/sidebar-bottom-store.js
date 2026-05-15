import { createStore } from "/js/AlpineStore.js";

const model = {
  versionNo: "",
  commitTime: "",

  get versionLabel() {
    if (this.versionNo && this.commitTime) {
      const v = this.versionNo.replace(/^M\s*/, "").replace(/^v/, "v");
      return `BioDockify ${v}`;
    }
    return "";
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

