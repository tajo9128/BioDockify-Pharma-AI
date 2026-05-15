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

  syncToCloud() {
    this.message = "Syncing to Google Drive...";
    setTimeout(() => { this.message = "Cloud sync not configured. Set up GDrive OAuth in Settings."; }, 1500);
    setTimeout(() => { this.message = ""; }, 6000);
  },

  createFullBackup() {
    this.message = "Full backup starting...";
    this.createBackup();
  },

  backupToPC() {
    this.message = "Preparing PC download... Open your Docker volume path or use docker cp to extract backups.";
    setTimeout(() => { this.message = ""; }, 5000);
  },

  retrieveBackup(method) {
    if (method === "local") { this.loadBackups(); this.message = "Local backups refreshed."; }
    else if (method === "cloud") { this.message = "Cloud restore: Visit Google Drive to download backup archive."; }
    else if (method === "pc") { this.message = "PC restore: Place backup file in usr/backups/ and refresh."; }
    setTimeout(() => { this.message = ""; }, 4000);
  },
});
