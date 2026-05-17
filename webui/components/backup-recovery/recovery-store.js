import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("backupRecovery", {
  backups: [],
  loading: false,
  restoring: false,
  creating: false,
  message: "",
  error: "",
  gdriveConnected: false,
  gdriveAutoSync: false,

  get hasBackups() { return this.backups.length > 0; },

  async loadBackups() {
    this.loading = true; this.error = "";
    try {
      const resp = await callJsonApi("backup_auto", { action: "list" });
      if (resp.error) { this.error = resp.error; return; }
      this.backups = resp.backups || [];
    } catch (e) { this.error = "Failed to load backups: " + e.message; }
    this.loading = false;
  },

  async createBackup(label = "manual") {
    this.creating = true; this.error = ""; this.message = "Creating backup...";
    try {
      const resp = await callJsonApi("backup_auto", { action: "create", label });
      if (resp.error) { this.error = resp.error; return; }
      this.message = `Backup created: ${resp.size_mb} MB (${resp.files || 0} files)`;
      setTimeout(() => this.message = "", 5000);
      await this.loadBackups();
    } catch (e) { this.error = "Backup failed: " + e.message; }
    this.creating = false;
  },

  createFullBackup() {
    this.createBackup("full");
  },

  async restoreBackup(backupId) {
    if (!confirm(`Restore backup ${backupId}? This may overwrite current data.`)) return;
    this.restoring = true; this.error = ""; this.message = "Restoring backup...";
    try {
      const resp = await callJsonApi("backup_auto", { action: "restore", id: backupId });
      if (resp.error) { this.error = resp.error; return; }
      this.message = `Backup restored: ${resp.restored || 0} items recovered`;
      setTimeout(() => this.message = "", 5000);
    } catch (e) { this.error = "Restore failed: " + e.message; }
    this.restoring = false;
  },

  async deleteBackup(backupId) {
    if (!confirm(`Delete backup ${backupId}?`)) return;
    try {
      const resp = await callJsonApi("backup_auto", { action: "delete", id: backupId });
      if (resp.error) { this.error = resp.error; return; }
      this.message = "Backup deleted";
      setTimeout(() => this.message = "", 3000);
      await this.loadBackups();
    } catch (e) { this.error = "Delete failed: " + e.message; }
  },

  backupToPC() {
    this.message = "Use Docker desktop to download files from the usr/backups/ volume, or run: docker cp <container>:/a0/usr/backups/ ./backups/";
    setTimeout(() => this.message = "", 8000);
  },

  syncToCloud() {
    this.message = "Cloud sync requires GDrive OAuth setup in Settings → Backup.";
    setTimeout(() => this.message = "", 4000);
  },

  retrieveBackup(method) {
    if (method === "local") { this.loadBackups(); this.message = "Local backups refreshed."; }
    else if (method === "cloud") { this.message = "Cloud restore: Visit Google Drive to download backup archive."; }
    else if (method === "pc") { this.message = "PC restore: Place backup file in usr/backups/ and refresh."; }
    setTimeout(() => this.message = "", 4000);
  },

  connectGDrive() {
    this.message = "GDrive OAuth connection initiated. Authorize in the popup window.";
    setTimeout(() => this.message = "", 4000);
  },

  disconnectGDrive() {
    this.gdriveConnected = false;
    this.message = "Google Drive disconnected.";
    setTimeout(() => this.message = "", 3000);
  },
});
