export default async function registerTrialScanner(canvas) {
  canvas.registerSurface({
    id: "trial-scanner",
    title: "Trial Scanner",
    icon: "clinical_notes",
    order: 31,
    modalPath: "/components/trial-scanner/trial-panel.html",
    open() {}, close() {},
  });
}
