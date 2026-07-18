export default async function registerQsarSurface(canvas) {
  canvas.registerSurface({
    id: "qsar",
    title: "QSAR Modeler",
    icon: "model_training",
    order: 24,
    modalPath: "/components/qsar3d/qsar3d.html",
  });
}
