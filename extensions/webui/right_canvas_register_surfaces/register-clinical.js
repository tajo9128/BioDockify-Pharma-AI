export default async function registerClinicalSurface(canvas) {
  canvas.registerSurface({
    id: "clinical",
    title: "Clinical Pharmacy",
    icon: "clinical_notes",
    order: 28,
    modalPath: "/components/clinical/clinical.html",
  });
}
