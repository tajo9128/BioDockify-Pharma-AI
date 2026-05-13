export default async function registerSlidesSurface(canvas) {
  canvas.registerSurface({
    id: "slides",
    title: "Slides",
    icon: "slideshow",
    order: 45,
    modalPath: "/components/slides/slides-modal.html",
    open() {},
    close() {},
  });
}
