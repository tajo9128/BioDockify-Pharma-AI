export default async function registerThesisSurface(canvas) {
  canvas.registerSurface({
    id: "thesis",
    title: "Thesis",
    icon: "description",
    order: 40,
    modalPath: "/components/thesis/thesis-modal.html",
    open() {},
    close() {},
  });
}
