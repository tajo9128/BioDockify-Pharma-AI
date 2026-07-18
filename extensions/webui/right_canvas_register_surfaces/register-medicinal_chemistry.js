export default async function registerMedicinalChemistrySurface(canvas) {
  canvas.registerSurface({
    id: "medicinal_chemistry",
    title: "Medicinal Chemistry",
    icon: "hexagon",
    order: 33,
    modalPath: "/components/medicinal_chemistry/medicinal_chemistry.html",
  });
}
