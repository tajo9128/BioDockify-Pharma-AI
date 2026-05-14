export default async function registerAdmet(canvas) {
  canvas.registerSurface({ id: "admet", title: "ADMET", icon: "monitor_heart", order: 27, modalPath: "/components/admet/admet-panel.html", open(){}, close(){} });
}
