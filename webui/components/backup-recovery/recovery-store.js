import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("backupRecovery", {
  backups: [],
  loading: false,
  restoring: false,
  creating: false,
  message: "",
  error: "",

  async loadBackups() {
    this.loading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("backup_auto", { action: "list" });
      if (resp.error) { this.error = resp.error; return; }
      this.backups = resp.backups || [];
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async createBackup() {
    this.creating = true;
    this.error = "";
    this.message = "";
    try {
      const resp = await callJsonApi("backup_auto", { action: "create", label: "manual" });
      if (resp.error) { this.error = resp.error; return; }
      this.message = `Backup created: ${resp.size_mb} MB, ${resp.files || 0} files`;
      await this.loadBackups();
    } catch (e) { this.error = e.message; }
    this.creating = false;
  },

  async restoreBackup(backupId) {
    if (!confirm(`Restore from ${backupId}? This will overwrite current data.`)) return;
    this.restoring = true;
    this.error = "";
    this.message = "";
    try {
      const resp = await callJsonApi("backup_auto", { action: "restore", id: backupId });
      if (resp.error) { this.error = resp.error; return; }
      this.message = `Restored successfully: ${resp.restored || 0} files`;
      await this.loadBackups();
    } catch (e) { this.error = e.message; }
    this.restoring = false;
  },

  async deleteBackup(backupId) {
    if (!confirm(`Delete backup ${backupId}?`)) return;
    try {
      await callJsonApi("backup_auto", { action: "delete", id: backupId });
      await this.loadBackups();
    } catch (e) { this.error = e.message; }
  },

  get hasBackups() { return this.backups.length > 0; }
});
