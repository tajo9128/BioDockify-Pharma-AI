export default async function registerWetLabSurface(canvas) {
  canvas.registerSurface({
    id: "wetlab",
    title: "Wet Lab",
    icon: "biotech",
    order: 50,
    modalPath: "/components/wetlab/wetlab-modal.html",
    open() {},
    close() {},
  });
}
