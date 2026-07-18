export default async function registerPharmacologySurface(canvas) {
  canvas.registerSurface({
    id: "pharmacology",
    title: "Pharmacology",
    icon: "monitor_heart",
    order: 32,
    modalPath: "/components/pharmacology/pharmacology.html",
  });
}
