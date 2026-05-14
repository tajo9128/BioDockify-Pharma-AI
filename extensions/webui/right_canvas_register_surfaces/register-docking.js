export default async function registerDocking(canvas) {
  canvas.registerSurface({
    id: "docking",
    title: "Docking",
    icon: "biotech",
    order: 23,
    modalPath: "/components/docking/docking-panel.html",
    open() {},
    close() {},
  });
}
