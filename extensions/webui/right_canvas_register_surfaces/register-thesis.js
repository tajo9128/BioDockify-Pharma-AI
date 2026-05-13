export default async function registerThesisSurface(canvas) {
  canvas.registerSurface({
    id: "thesis",
    title: "Academic Writer",
    icon: "description",
    order: 40,
    modalPath: "/components/thesis/thesis-modal.html",
    open() {},
    close() {},
  });
}
