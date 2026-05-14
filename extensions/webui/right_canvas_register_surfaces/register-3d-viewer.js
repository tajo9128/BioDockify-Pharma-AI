export default async function register3dViewer(canvas) {
  canvas.registerSurface({ id: "viewer3d", title: "3D Viewer", icon: "view_in_ar", order: 24, modalPath: "/components/3d-viewer/3d-viewer-panel.html", open(){}, close(){} });
}
