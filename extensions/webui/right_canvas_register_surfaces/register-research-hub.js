export default async function registerResearchHub(canvas) {
  canvas.registerSurface({
    id: "research-hub",
    title: "Research Tools",
    icon: "science",
    order: 10,
    modalPath: "/components/research/research-tools.html",
    open() {},
    close() {},
  });
}
