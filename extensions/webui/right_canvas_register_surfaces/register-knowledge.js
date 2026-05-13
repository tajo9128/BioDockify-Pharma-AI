export default async function registerKnowledgeSurface(canvas) {
  canvas.registerSurface({
    id: "knowledge",
    title: "Knowledge",
    icon: "psychology",
    order: 60,
    modalPath: "/components/knowledge/knowledge-modal.html",
    open() {},
    close() {},
  });
}
