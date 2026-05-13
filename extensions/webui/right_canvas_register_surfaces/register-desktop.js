export default async function registerDesktopSurface(canvas) {
  canvas.registerSurface({
    id: "desktop",
    title: "Desktop",
    icon: "desktop_windows",
    order: 5,
    modalPath: "/components/desktop/desktop-panel.html",
    open() {},
    close() {},
  });
}
