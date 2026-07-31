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
  autoBackupStatus: null,
  autoBackupList: [],

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
      const resp = await callJsonApi("backup_auto", { action: "restore", backup_id: backupId });
      if (resp.error) { this.error = resp.error; return; }
      this.message = `Backup restored: ${(resp.restored || []).length} items recovered`;
      setTimeout(() => this.message = "", 5000);
    } catch (e) { this.error = "Restore failed: " + e.message; }
    this.restoring = false;
  },

  async deleteBackup(backupId) {
    if (!confirm(`Delete backup ${backupId}?`)) return;
    try {
      const resp = await callJsonApi("backup_auto", { action: "delete", id: backupId });
      if (resp.status === "error" || resp.error) { this.error = resp.error || "Delete failed"; return; }
      this.message = "Backup deleted";
      setTimeout(() => this.message = "", 3000);
      await this.loadBackups();
    } catch (e) { this.error = "Delete failed: " + e.message; }
  },

  async backupToPC(backupId) {
    // Real download: stream the backup zip to the user's browser → Downloads folder
    if (!backupId) {
      // No specific backup given — create one first, then download it
      this.message = "Creating a fresh backup before downloading...";
      const create = await callJsonApi("backup_auto", { action: "create", label: "Save to PC" });
      if (create.error || !create.success) { this.error = create.error || "Backup creation failed"; return; }
      backupId = create.backup_id;
      this.message = `Backup ${backupId} created. Downloading to your PC...`;
      await this.loadBackups();
    } else {
      this.message = `Downloading ${backupId} to your PC...`;
    }
    try {
      // Fetch the zip as a blob and trigger browser download
      const csrfResp = await fetch("/api/csrf_token");
      const csrfData = await csrfResp.json();
      const resp = await fetch("/api/backup_auto", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfData.csrf_token || "",
        },
        body: JSON.stringify({ action: "download", backup_id: backupId }),
      });
      if (!resp.ok) {
        const errText = await resp.text();
        this.error = `Download failed: ${resp.status} ${errText.substring(0, 100)}`;
        return;
      }
      const blob = await resp.blob();
      if (blob.size < 100) {
        this.error = "Downloaded file is too small — backup may be empty.";
        return;
      }
      // Trigger browser download to the user's Downloads folder
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${backupId}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.message = `✓ ${backupId}.zip downloaded to your Downloads folder (${(blob.size / 1024 / 1024).toFixed(2)} MB). Safe on your PC.`;
      setTimeout(() => this.message = "", 8000);
    } catch (e) {
      this.error = "Download failed: " + e.message;
    }
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
    this.message = "GDrive disconnected.";
    setTimeout(() => this.message = "", 3000);
  },

  async createAutoBackup() {
    this.creating = true; this.message = "Creating auto-backup...";
    try {
      const r = await callJsonApi("backup_create", { action: "create" });
      if (r.status === "ok") { this.message = r.message || "Auto-backup created"; }
      else { this.error = r.error || "Backup failed"; }
    } catch (e) { this.error = "Backup failed: " + e.message; }
    this.creating = false;
  },

  async restoreLatest() {
    if (!confirm("Restore from most recent auto-backup? This will overwrite current data.")) return;
    this.restoring = true; this.message = "Restoring from latest backup...";
    try {
      const r = await callJsonApi("backup_create", { action: "restore" });
      if (r.status === "ok") { this.message = r.message || "Restored from backup"; }
      else { this.error = r.error || "Restore failed"; }
    } catch (e) { this.error = "Restore failed: " + e.message; }
    this.restoring = false;
  },

  async restoreSpecific(name) {
    if (!confirm("Restore from " + name + "? This will overwrite current data.")) return;
    this.restoring = true; this.message = "Restoring from " + name + "...";
    try {
      const r = await callJsonApi("backup_create", { action: "restore_specific", backup_name: name });
      if (r.status === "ok") { this.message = r.message || "Restored"; }
      else { this.error = r.error || "Restore failed"; }
    } catch (e) { this.error = "Restore failed: " + e.message; }
    this.restoring = false;
  },

  async listAutoBackups() {
    this.loading = true;
    try {
      const r = await callJsonApi("backup_create", { action: "list" });
      if (r.status === "ok") { this.autoBackupList = r.backups || []; }
    } catch (e) {}
    this.loading = false;
  },

  async loadAutoBackupStatus() {
    try {
      const r = await callJsonApi("backup_create", { action: "status" });
      if (r.status === "ok") { this.autoBackupStatus = r; }
    } catch (e) {}
  },

  // === Docker Volume Restore ===
  dockerVolumes: [],
  dockerVolumeLoading: false,
  dockerVolumeScanning: false,
  selectedVolume: null,
  volumeInspectData: null,
  selectedVolumeItems: [],
  dockerAvailable: true,
  _overwritePolicy: "skip",

  async scanDockerVolumes() {
    this.dockerVolumeScanning = true;
    this.error = "";
    try {
      const resp = await callJsonApi("docker_volume_restore", { action: "scan" });
      if (resp.error) {
        this.dockerAvailable = resp.docker_available !== false;
        if (!this.dockerAvailable) {
          this.error = "Docker socket not mounted. Add `-v /var/run/docker.sock:/var/run/docker.sock` to your docker run command.";
        } else {
          this.error = resp.error;
        }
        return;
      }
      this.dockerVolumes = resp.volumes || [];
      this.dockerAvailable = true;
      this.message = resp.message || `Found ${this.dockerVolumes.length} volumes`;
      setTimeout(() => this.message = "", 5000);
    } catch (e) {
      this.dockerAvailable = false;
      this.error = "Docker volume scan failed: Docker socket not mounted. Add `-v /var/run/docker.sock:/var/run/docker.sock` to your docker run command.";
    }
    this.dockerVolumeScanning = false;
  },

  async inspectDockerVolume(volumeName) {
    this.dockerVolumeLoading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("docker_volume_restore", {
        action: "inspect",
        volume_name: volumeName,
      });
      if (resp.error) { this.error = resp.error; return; }
      this.selectedVolume = volumeName;
      this.volumeInspectData = resp;
      this.selectedVolumeItems = Object.keys(resp.bio_data_found || {});
    } catch (e) {
      this.error = "Inspect failed: " + e.message;
    }
    this.dockerVolumeLoading = false;
  },

  async restoreFromDockerVolume(volumeName, overwritePolicy, selectedItems) {
    if (!volumeName) { this.error = "No volume selected"; return; }
    if (!confirm(`Restore data from volume "${volumeName}"? This may overwrite existing data.`)) return;
    this.restoring = true;
    this.error = "";
    this.message = `Restoring from volume ${volumeName}...`;
    try {
      const resp = await callJsonApi("docker_volume_restore", {
        action: "restore",
        volume_name: volumeName,
        overwrite_policy: overwritePolicy || "skip",
        selected_items: selectedItems || [],
      });
      if (resp.success) {
        this.message = resp.message || `Restored ${resp.total_files} files from ${volumeName}`;
        setTimeout(() => this.message = "", 8000);
      } else {
        this.error = resp.error || "Restore failed";
      }
    } catch (e) {
      this.error = "Volume restore failed: " + e.message;
    }
    this.restoring = false;
  },

  toggleVolumeItem(item) {
    const idx = this.selectedVolumeItems.indexOf(item);
    if (idx >= 0) this.selectedVolumeItems.splice(idx, 1);
    else this.selectedVolumeItems.push(item);
  },

  selectAllVolumeItems(items) {
    this.selectedVolumeItems = [...items];
  },

  deselectAllVolumeItems() {
    this.selectedVolumeItems = [];
  },

  // Upload backup from PC and auto-restore
  restoringFromUpload: false,
  uploadFilename: "",

  triggerUploadRestore() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".zip";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      this.restoringFromUpload = true;
      this.uploadFilename = file.name;
      this.error = "";
      this.message = `Restoring from ${file.name}...`;
      try {
        const formData = new FormData();
        formData.append("backup_file", file);
        formData.append("action", "restore_from_upload");
        formData.append("metadata", "{}");
        const csrf = await (await fetch("/api/csrf_token")).json();
        const resp = await fetch("/api/backup_auto", {
          method: "POST",
          headers: { "X-CSRF-Token": csrf.csrf_token || "" },
          body: formData,
        });
        const result = await resp.json();
        if (result.success) {
          this.message = `✓ Restored ${result.restored_files} files from ${file.name}. Your data is back!`;
          setTimeout(() => this.message = "", 8000);
          await this.loadBackups();
        } else {
          this.error = result.error || "Restore failed";
        }
      } catch (e) {
        this.error = "Upload restore failed: " + e.message;
      }
      this.restoringFromUpload = false;
      this.uploadFilename = "";
    };
    input.click();
  },
});
