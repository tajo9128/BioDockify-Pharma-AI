export default async function registerQSAR3DSurface(canvas) {
  canvas.registerSurface({
    id: "qsar3d",
    title: "3D-QSAR",
    icon: "science",
    order: 26,
    modalPath: "/components/qsar3d/qsar3d.html",
  });
}
