export default async function registerDockingAnalysisSurface(canvas) {
  canvas.registerSurface({
    id: "docking-analysis",
    title: "Docking Analysis",
    icon: "biotech",
    order: 26.5,
    modalPath: "/components/docking-analysis/docking-analysis.html",
    async open(payload = {}) {
      if (payload.jobId) {
        const store = globalThis.Alpine?.store?.("dockingAnalysis");
        if (store) { store.jobId = payload.jobId; await store.analyze(); }
      }
    },
  });
}
