export default async function registerPharmaAnalysisSurface(canvas) {
  canvas.registerSurface({
    id: "pharma-analysis",
    title: "Pharma Analysis",
    icon: "biotech",
    order: 29,
    modalPath: "/components/pharma-analysis/pharma-analysis.html",
  });
}
