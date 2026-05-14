export default async function registerDrugBrowser(canvas) {
  canvas.registerSurface({ id: "drug-browser", title: "Drug Browser", icon: "medication_liquid", order: 26, modalPath: "/components/drug-browser/drug-browser-panel.html", open(){}, close(){} });
}
