import { createStore } from "/js/AlpineStore.js";

export const store = createStore("biodockifyUpdate", {
  currentVersion: "",
  latestVersion: "",
  updateAvailable: false,
  checked: false,
  checking: false,
  error: "",

  async checkForUpdate() {
    if (this.checking) return;
    this.checking = true;
    this.error = "";
    this.currentVersion = globalThis.gitinfo?.version || "v4.1.8";
    try {
      const resp = await fetch("/api/biodockify/update-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_version: this.currentVersion })
      });
      const data = await resp.json();
      this.latestVersion = data.latest_version || this.currentVersion;
      this.updateAvailable = data.update_available === true;
      this.checked = true;
    } catch (e) {
      this.error = "Could not check for updates";
      this.checked = false;
    }
    this.checking = false;
  }
});
