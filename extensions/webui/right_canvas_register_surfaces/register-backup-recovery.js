export default async function registerBackupRecovery(canvas) {
  canvas.registerSurface({
    id: "backup-recovery",
    title: "Backup",
    icon: "backup",
    order: 35,
    modalPath: "/components/backup-recovery/recovery-panel.html",
    open() {}, close() {},
  });
}
