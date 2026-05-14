export default async function registerDrugProperties(canvas) {
  canvas.registerSurface({
    id: "drug-properties",
    title: "Drug Properties",
    icon: "medication",
    order: 22,
    modalPath: "/components/drug-properties/drug-properties-panel.html",
    open() {},
    close() {},
  });
}
