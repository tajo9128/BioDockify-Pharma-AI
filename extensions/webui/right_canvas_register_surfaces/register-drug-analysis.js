export default async function registerDrugAnalysisSurface(canvas) {
  canvas.registerSurface({
    id: "drug-analysis",
    title: "Drug Analysis",
    icon: "medication",
    order: 23,
    modalPath: "/components/drug-analysis/drug-analysis.html",
  });
}
