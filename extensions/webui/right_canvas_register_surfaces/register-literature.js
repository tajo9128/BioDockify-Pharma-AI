export default async function registerLiteratureSurface(canvas) {
  canvas.registerSurface({
    id: "literature",
    title: "Literature",
    icon: "menu_book",
    order: 30,
    modalPath: "/components/literature/literature-modal.html",
    open() {},
    close() {},
  });
}
