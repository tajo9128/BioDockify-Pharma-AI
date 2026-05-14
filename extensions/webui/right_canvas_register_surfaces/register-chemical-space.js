export default async function registerChemicalSpace(canvas) {
  canvas.registerSurface({ id: "chemical-space", title: "Chemical Space", icon: "bubble_chart", order: 29, modalPath: "/components/chemical-space/chemspace-panel.html", open(){}, close(){} });
}
