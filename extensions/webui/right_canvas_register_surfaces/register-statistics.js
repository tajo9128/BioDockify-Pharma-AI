export default async function registerStatisticsSurface(canvas) {
  canvas.registerSurface({
    id: "statistics",
    title: "Statistics",
    icon: "analytics",
    order: 20,
    modalPath: "/components/statistics/statistics-modal.html",
    open() {},
    close() {},
  });
}
