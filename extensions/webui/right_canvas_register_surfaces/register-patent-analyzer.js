export default async function registerPatentAnalyzer(canvas) {
  canvas.registerSurface({
    id: "patent-analyzer",
    title: "Patent Analyzer",
    icon: "gavel",
    order: 30,
    modalPath: "/components/patent-analyzer/patent-panel.html",
    open() {}, close() {},
  });
}
